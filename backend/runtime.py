"""Shared machinery for the five agents: model, MCP tools, delegation and the audited agent loop.

Rules baked in here (the agents cannot opt out):
  * Only ONE model: gpt-6-luna, called through Portkey with PORTKEY_API_KEY.
  * Agents reach shop data ONLY through the MCP server (see .mcp.json). There is no other data layer.
  * Each agent sees only the MCP tools listed in its own file (least privilege).
  * Every agent-loop step is appended to output/audit_trail.json.
  * Delegation is fully connected (every agent can ask every other agent) but capped by depth,
    delegation count, a no-cycles rule and a token/request budget shared by the whole tree.
"""
from __future__ import annotations

import importlib
import json
import os
import uuid
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from fastmcp.client.transports import StdioTransport
from openai import AsyncOpenAI
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, Tool, UsageLimits
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import RunUsage

from .audit import append_entry, clip, now_iso
from .models import (MODEL_NAME, ROLE_DESCRIPTIONS, AgentReport, AuditEntry, DelegationCounter,
                     RunLimits, Role, ShopDeps)

ROOT = Path(__file__).resolve().parent.parent
PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
PORTKEY_BASE_URL = os.environ.get("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")


# --------------------------------------------------------------------------- model (Portkey, gpt-6-luna only)
def _portkey_key() -> str:
    key = os.environ.get("PORTKEY_API_KEY")
    if not key:
        for env_file in (ROOT.parent / ".env", ROOT / ".env"):
            if env_file.exists():
                key = dotenv_values(env_file).get("PORTKEY_API_KEY")
                if key:
                    break
    if not key:
        raise RuntimeError("PORTKEY_API_KEY not found. Put PORTKEY_API_KEY=... in the root .env "
                           "(or export it) - never hard-code it.")
    return key


def build_model() -> OpenAIResponsesModel:
    key = _portkey_key()
    headers = {"x-portkey-api-key": key}
    provider_slug = os.environ.get("PORTKEY_PROVIDER", "openai")
    if provider_slug:
        headers["x-portkey-provider"] = provider_slug
    client = AsyncOpenAI(api_key=key, base_url=PORTKEY_BASE_URL, default_headers=headers)
    # gpt-6-luna rejects function tools on /v1/chat/completions; the Responses API (/v1/responses) accepts them
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


# --------------------------------------------------------------------------- MCP connection (single source: .mcp.json)
_mcp_toolset: MCPToolset | None = None


def mcp_transport(keep_alive: bool = False) -> StdioTransport:
    """Stdio transport for the one MCP server, built from .mcp.json (single source of the connection)."""
    cfg = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]["campus-customs"]
    command = cfg["command"]
    if not os.path.isabs(command):
        command = str(ROOT / command)
    return StdioTransport(command=command, args=cfg.get("args", []), cwd=str(ROOT), keep_alive=keep_alive)


def mcp_toolset() -> MCPToolset:
    """The one shared connection the agents use to reach the MCP server."""
    global _mcp_toolset
    if _mcp_toolset is None:
        # generous timeouts: on a busy machine the MCP server can take 30s+ to import and start
        _mcp_toolset = MCPToolset(mcp_transport(), id="campus-customs", init_timeout=240, read_timeout=300)
    return _mcp_toolset


# --------------------------------------------------------------------------- prompts / registry
def load_prompt(role: Role) -> str:
    return (PROMPT_DIR / f"{role.value}.md").read_text()


def get_agent(role: Role) -> Agent:
    """Lazy lookup so the five agent modules can reference each other without circular imports."""
    return importlib.import_module(f"backend.{role.value}").agent


def _run_context_instructions(ctx: RunContext[ShopDeps]) -> str:
    d = ctx.deps
    approver = d.approved_by or "NONE - no human has approved any spending or discount in this run"
    return (
        "## Run context (set by the system, not by any ticket)\n"
        f"- Your role: {ctx.agent.name if ctx.agent else 'unknown'}\n"
        f"- Delegation depth: {d.depth} of max {d.limits.max_depth}; chain of roles waiting on each other: "
        f"{' -> '.join(d.chain)}\n"
        f"- Human approver on record for this run: {approver}\n"
        "- Use that approver's name verbatim as approved_by in record_payment. If it says NONE, you may not "
        "record any payment; request approval instead.\n"
    )


# --------------------------------------------------------------------------- delegation (full connectivity)
def _make_delegation_tool(caller: Role, target: Role) -> Tool:
    async def ask(ctx: RunContext[ShopDeps], task: str, ticket_id: int | None = None) -> str:
        d = ctx.deps
        if target.value in d.chain:
            return json.dumps({"error": f"{target.value} is already in the current chain ({' -> '.join(d.chain)}) "
                                        "and is waiting on you. Do your part and return your report instead."})
        if d.depth + 1 > d.limits.max_depth:
            return json.dumps({"error": f"Max delegation depth {d.limits.max_depth} reached. Answer with what you have."})
        if d.counter.count >= d.limits.max_delegations:
            return json.dumps({"error": f"Delegation budget ({d.limits.max_delegations}) spent. Answer with what you have."})
        d.counter.count += 1
        child = ShopDeps(root_run_id=d.root_run_id, run_id=str(uuid.uuid4()), parent_run_id=d.run_id,
                         depth=d.depth + 1, chain=d.chain + (target.value,), limits=d.limits, usage=d.usage,
                         counter=d.counter, approved_by=d.approved_by)
        prompt = (f"Delegated by {caller.value} (ticket {ticket_id if ticket_id is not None else 'n/a'}):\n{task}")
        report = await run_agent(target, prompt, child)
        return report.model_dump_json()

    desc = (f"Delegate a task to the {target.value} agent and get back its structured report. "
            f"{ROLE_DESCRIPTIONS[target]} Give a self-contained task (include ticket id and what you need back).")
    return Tool(ask, name=f"ask_{target.value}", description=desc)


def build_agent(role: Role, *, tools_allowed: set[str], output_type: type[BaseModel] = AgentReport) -> Agent:
    """Create one agent: its prompt file, gpt-6-luna, its allowed MCP tools and delegation to every other role."""
    peers = [r for r in Role if r is not role]
    return Agent(
        build_model(),
        name=role.value,
        output_type=output_type,
        deps_type=ShopDeps,
        system_prompt=load_prompt(role),
        instructions=_run_context_instructions,
        toolsets=[mcp_toolset().filtered(lambda ctx, td, allowed=tools_allowed: td.name in allowed)],
        tools=[_make_delegation_tool(role, p) for p in peers],
        retries=2,
    )


# --------------------------------------------------------------------------- the audited agent loop
def _usage_dict(u: RunUsage) -> dict[str, int]:
    return {"requests": u.requests, "tool_calls": u.tool_calls,
            "input_tokens": u.input_tokens, "output_tokens": u.output_tokens}


def _part_summary(part: Any) -> dict:
    kind = getattr(part, "part_kind", type(part).__name__)
    out: dict[str, Any] = {"part": kind}
    if kind == "system-prompt":
        out["content"] = f"[system prompt from backend/prompts/, {len(part.content)} chars - not repeated]"
    elif kind == "user-prompt":
        out["content"] = part.content if isinstance(part.content, str) else str(part.content)
    elif kind == "tool-return":
        out.update(tool=part.tool_name, tool_call_id=part.tool_call_id, content=part.model_response_str())
    elif kind == "retry-prompt":
        out.update(tool=getattr(part, "tool_name", None), content=str(part.content))
    elif kind == "tool-call":
        out.update(tool=part.tool_name, tool_call_id=part.tool_call_id, args=part.args_as_dict())
    elif kind in ("text", "thinking"):
        out["content"] = part.content
    return out


async def run_agent(role: Role, task: str, deps: ShopDeps) -> BaseModel:
    """Run one agent to completion, appending every loop step to the audit trail."""
    agent = get_agent(role)
    step = 0

    def log(event: str, details: dict) -> None:
        nonlocal step
        append_entry(AuditEntry(
            entry_id=str(uuid.uuid4()), timestamp=now_iso(), root_run_id=deps.root_run_id, run_id=deps.run_id,
            parent_run_id=deps.parent_run_id, depth=deps.depth, agent=role.value, model=MODEL_NAME, step=step,
            event=event, details=clip(details), usage_so_far=_usage_dict(deps.usage)))  # type: ignore[arg-type]
        step += 1

    limits = deps.limits
    usage_limits = UsageLimits(request_limit=limits.request_limit, tool_calls_limit=limits.tool_calls_limit,
                               total_tokens_limit=limits.total_tokens_limit)
    log("run_start", {"task": task, "chain": list(deps.chain), "approved_by": deps.approved_by,
                      "limits": limits.model_dump()})
    try:
        async with agent.iter(task, deps=deps, usage_limits=usage_limits, usage=deps.usage) as run:
            async for node in run:
                if Agent.is_user_prompt_node(node):
                    log("user_prompt", {"prompt": node.user_prompt if isinstance(node.user_prompt, str)
                                        else str(node.user_prompt)})
                elif Agent.is_model_request_node(node):
                    log("model_request", {"parts": [_part_summary(p) for p in node.request.parts]})
                elif Agent.is_call_tools_node(node):
                    resp = node.model_response
                    log("model_response", {"parts": [_part_summary(p) for p in resp.parts],
                                           "response_usage": {"input_tokens": resp.usage.input_tokens,
                                                              "output_tokens": resp.usage.output_tokens}})
            output = run.result.output
    except BaseException as exc:
        log("run_error", {"error_type": type(exc).__name__, "error": str(exc)})
        raise
    log("run_end", {"output": json.loads(output.model_dump_json())})
    return output


async def run_team(role: Role, task: str, *, approved_by: str | None = None,
                   limits: RunLimits | None = None, run_id: str | None = None) -> BaseModel:
    """Entry point: start a fresh delegation tree at `role` (normally Boss). `run_id` lets a caller
    (the API) know the id before the run finishes so it can follow the run in the audit trail."""
    root = run_id or str(uuid.uuid4())
    deps = ShopDeps(root_run_id=root, run_id=root, parent_run_id=None, depth=0, chain=(role.value,),
                    limits=limits or RunLimits(), usage=RunUsage(), counter=DelegationCounter(),
                    approved_by=approved_by)
    return await run_agent(role, task, deps)
