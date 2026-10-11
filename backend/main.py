"""FastAPI backend for the dashboard.

Start it from this folder:   uvicorn main:app --reload --port 8000     (http://localhost:8000)

Every read/write of shop data goes through the MCP server (one persistent client opened at startup); the
routes never touch the working database directly, except Reset, which restores it from the original file.
Agents can only PREPARE a payment. The approve route below is the only code path that changes cash, and it
runs only when a person clicks Approve.
"""
import asyncio
import json
import sqlite3
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:          # lets `uvicorn main:app` work from backend/ with absolute imports
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import Client

from backend.audit import audit_path, clip, now_iso
from backend.models import (AgentEvent, ApprovePaymentRequest, PendingPayment, ResolveTicketRequest, Role, RunStatus,
                            TicketView)
from backend.runtime import mcp_transport, run_team

ORIGINAL_DB = ROOT / "data" / "campus_customs.db"
WORKING_DB = ROOT / "data" / "campus_customs_new.db"

mcp_client: Client | None = None
runs: dict[str, RunStatus] = {}          # in-memory run registry (the audit trail is the durable record)
active_run: str | None = None            # only one agent run at a time: agents share one cash account


@asynccontextmanager
async def lifespan(app: FastAPI):
    global mcp_client
    async with Client(mcp_transport(keep_alive=True)) as client:
        mcp_client = client
        yield
    mcp_client = None


app = FastAPI(title="Campus Customs backend", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
                   allow_methods=["*"], allow_headers=["*"])


# --------------------------------------------------------------------------- helpers
async def mcp(tool: str, **args: Any) -> dict:
    """Call one MCP tool and return its dict result."""
    if mcp_client is None:
        raise HTTPException(503, "MCP server connection is not ready")
    result = await mcp_client.call_tool(tool, args)
    return result.data


def _ticket_state(status: str) -> str:
    return "resolved" if status == "resolved" else "open"


async def _ticket_views() -> list[TicketView]:
    tickets = (await mcp("list_tickets"))["tickets"]
    invoices = {i["id"]: i for i in (await mcp("list_invoices"))["invoices"]}
    leases = {l["id"]: l for l in (await mcp("list_leases"))["leases"]}
    rent_paid = {p["ref_id"] for p in (await mcp("list_payments", kind="rent"))["payments"]}
    views = []
    for t in tickets:
        pending = None
        inv, lease = invoices.get(t["invoice_id"]), leases.get(t["lease_id"])
        if inv:   # a linked vendor invoice: payable while it is still open
            pending = PendingPayment(kind="invoice", ref_id=inv["id"], amount=inv["amount"], payee=inv["vendor_name"],
                                     due_date=inv["due_date"], already_paid=inv["status"] != "open")
        elif lease:  # a linked lease: rent counts as paid once any rent payment is recorded for it
            pending = PendingPayment(kind="rent", ref_id=lease["id"], amount=lease["monthly_rent"],
                                     payee=lease["landlord"], due_date=lease["next_due"],
                                     already_paid=lease["id"] in rent_paid)
        views.append(TicketView(
            id=t["id"], type=t["type"], requester=t["requester"], subject=t["subject"], sku=t["sku"],
            size=t["size"], qty=t["qty"], status=t["status"], state=_ticket_state(t["status"]),
            awaiting_approval=t["status"] == "waiting_approval", notes=t["notes"], created_at=t["created_at"],
            pending_payment=pending,
            run_status="running" if any(r.ticket_id == t["id"] and r.status == "running" for r in runs.values()) else "idle",
            last_run_id=next((r.run_id for r in reversed(list(runs.values())) if r.ticket_id == t["id"]), None)))
    return views


def _shape_event(index: int, e: dict) -> AgentEvent:
    """Turn a raw audit entry into what the board needs: who said what, which tools, what came back."""
    d, ev = e["details"], e["event"]
    out = AgentEvent(index=index, timestamp=e["timestamp"], root_run_id=e["root_run_id"], run_id=e["run_id"],
                     parent_run_id=e["parent_run_id"], depth=e["depth"], agent=e["agent"], step=e["step"],
                     event=ev, usage=e["usage_so_far"])
    if ev == "run_start":
        out.task = d.get("task")
    elif ev == "model_response":
        texts = []
        for p in d.get("parts", []):
            if p["part"] == "text" and p.get("content"):
                texts.append(p["content"])
            elif p["part"] == "tool-call" and p.get("tool") == "final_result":
                texts.append(str(p["args"].get("summary", "")))   # the structured final answer
            elif p["part"] == "tool-call":
                call = {"tool": p["tool"], "args": p["args"], "id": p.get("tool_call_id")}
                if p["tool"].startswith("ask_"):
                    call["delegates_to"] = p["tool"][4:]
                out.tool_calls.append(call)
        out.said = "\n".join(t for t in texts if t) or None
    elif ev == "model_request":
        for p in d.get("parts", []):
            if p["part"] == "tool-return":
                out.tool_results.append({"tool": p["tool"], "id": p.get("tool_call_id"), "content": p["content"][:1500]})
            elif p["part"] == "retry-prompt":
                out.tool_results.append({"tool": p.get("tool"), "id": p.get("tool_call_id"), "error": p["content"][:500]})
    elif ev == "run_end":
        output = d.get("output", {})
        out.said = output.get("summary")
        out.output = output
    elif ev == "run_error":
        out.error = f'{d.get("error_type")}: {d.get("error")}'
    return out


def _read_audit() -> list[dict]:
    path = audit_path()
    if not path.exists() or path.stat().st_size == 0:
        return []
    return json.loads(path.read_text())


# --------------------------------------------------------------------------- 1. tickets
@app.get("/api/tickets", response_model=list[TicketView])
async def list_tickets():
    """Every ticket with its status, whether it is open or resolved, and any payment awaiting approval."""
    return await _ticket_views()


# --------------------------------------------------------------------------- 2. run the agent team on a ticket
async def _run_ticket(run_id: str, ticket: dict) -> None:
    global active_run
    task = (f"Work ticket {ticket['id']} ONLY (type: {ticket['type']}). Do not work any other ticket. Follow your "
            "standard procedure, delegate only to the specialists this ticket needs, and set the ticket status. "
            "No human approver is on record for this run, so do NOT record any payment: prepare the payment or "
            "discount as an approval request and set the ticket to waiting_approval. A person approves from the "
            "dashboard.")
    status = runs[run_id]
    try:
        result = await run_team(Role.BOSS, task, run_id=run_id)    # no approved_by: agents cannot move money
        status.result, status.status = json.loads(result.model_dump_json()), "done"
        await _close_out_ticket(ticket["id"])
    except BaseException as exc:                                    # keep the failure visible to the board
        status.error, status.status = f"{type(exc).__name__}: {exc}", "error"
    finally:
        status.finished_at = now_iso()
        active_run = None


async def _close_out_ticket(ticket_id: int) -> None:
    """When a run finishes: a ticket that needs no human is marked resolved; one with an unpaid linked payment is
    parked at waiting_approval; one the agents already put at waiting_approval/escalated/resolved is left alone."""
    view = next(v for v in await _ticket_views() if v.id == ticket_id)
    if view.status in ("resolved", "waiting_approval", "escalated"):
        return
    if view.pending_payment and not view.pending_payment.already_paid:
        await mcp("update_ticket_status", ticket_id=ticket_id, status="waiting_approval", actor="dashboard",
                  note="Run finished with a payment still unpaid; a person must approve it.")
    else:
        await mcp("update_ticket_status", ticket_id=ticket_id, status="resolved", actor="dashboard",
                  note="Agent run finished and nothing is waiting on a person.")


@app.post("/api/tickets/{ticket_id}/run", response_model=RunStatus, status_code=202)
async def run_ticket(ticket_id: int):
    """Start the agent team (Boss first) on one ticket in the background; poll /api/runs/{run_id} and /api/events."""
    global active_run
    ticket = await mcp("get_ticket", ticket_id=ticket_id)
    if "error" in ticket:
        raise HTTPException(404, ticket["error"])
    if ticket["status"] == "resolved":
        raise HTTPException(409, f"Ticket {ticket_id} is already resolved")
    if active_run is not None:
        raise HTTPException(409, "An agent run is already in progress; wait for it to finish")
    run_id = str(uuid.uuid4())
    active_run = run_id
    runs[run_id] = RunStatus(run_id=run_id, ticket_id=ticket_id, status="running", started_at=now_iso())
    asyncio.create_task(_run_ticket(run_id, ticket))
    return runs[run_id]


@app.get("/api/runs/{run_id}", response_model=RunStatus)
async def get_run(run_id: str):
    """Status of a run started above, and the Boss's final report once it is done."""
    if run_id not in runs:
        raise HTTPException(404, "Unknown run id")
    return runs[run_id]


# --------------------------------------------------------------------------- 3. recent agent events
@app.get("/api/events")
async def recent_events(limit: int = Query(100, ge=1, le=1000), after: int | None = Query(None, ge=-1),
                        run_id: str | None = None):
    """Recent agent events from the audit trail: what each agent said, the tools it called, what came back.

    Without `after`: the last `limit` events. With `after` (the `next_after` from the previous call): only newer ones.
    `run_id` limits it to one run (the id returned by the run route).
    """
    rows = _read_audit()
    indexed = [(i, r) for i, r in enumerate(rows) if run_id is None or r["root_run_id"] == run_id]
    picked = indexed[-limit:] if after is None else [(i, r) for i, r in indexed if i > after][:limit]
    events = [_shape_event(i, r) for i, r in picked]
    return {"total": len(rows), "next_after": events[-1].index if events else (after if after is not None else len(rows) - 1),
            "events": events}


# --------------------------------------------------------------------------- 4. human approval of a payment
@app.post("/api/tickets/{ticket_id}/approve-payment")
async def approve_payment(ticket_id: int, body: ApprovePaymentRequest):
    """Pay the invoice or rent linked to a ticket, ONLY because a person clicked Approve.

    The amount, payee and kind come from the database through the ticket's links, never from the client. The
    ticket must be waiting_approval (i.e. agents prepared it), and the MCP tool still enforces its own rules
    (exact amount, no overdraft, no double payment, named human approver).
    """
    view = next((v for v in await _ticket_views() if v.id == ticket_id), None)
    if view is None:
        raise HTTPException(404, f"No ticket with id={ticket_id}")
    if view.run_status == "running":
        raise HTTPException(409, "Agents are still working on this ticket")
    if not view.awaiting_approval:
        raise HTTPException(409, f"Ticket {ticket_id} is {view.status!r}; agents have not prepared anything to approve")
    pay = view.pending_payment
    if pay is None:
        raise HTTPException(422, "This ticket has no payment to approve (a discount is a human decision, not a payment)")
    if pay.already_paid:
        raise HTTPException(409, "That payment has already been recorded")
    account = body.account
    if account is None:
        accounts = (await mcp("list_cash_accounts"))["accounts"]
        if len(accounts) != 1:
            raise HTTPException(422, "Several cash accounts exist; send `account`")
        account = accounts[0]["name"]
    result = await mcp("record_payment", kind=pay.kind, ref_id=pay.ref_id, amount=pay.amount, account=account,
                       approved_by=body.approved_by.strip(), actor="dashboard")
    if "error" in result:
        raise HTTPException(422, result["error"])
    note = (f"{pay.kind} payment of ${pay.amount:,.2f} to {pay.payee} approved by {body.approved_by.strip()} "
            f"and recorded (payment {result['payment_id']}).")
    await mcp("add_ticket_note", ticket_id=ticket_id, actor="dashboard", note=note)
    new_status = "resolved"            # the approval was the last human step the team was waiting for
    await mcp("update_ticket_status", ticket_id=ticket_id, status=new_status, actor="dashboard",
              note=f"Resolved after approved {pay.kind} payment.")
    return {"payment": result, "ticket_status": new_status, "new_balance": result["new_balance"]}


@app.post("/api/tickets/{ticket_id}/resolve")
async def resolve_ticket(ticket_id: int, body: ResolveTicketRequest):
    """A person accepts the team's recommendation on a ticket that needs a decision but no payment (e.g. a discount)."""
    view = next((v for v in await _ticket_views() if v.id == ticket_id), None)
    if view is None:
        raise HTTPException(404, f"No ticket with id={ticket_id}")
    name = body.approved_by.strip()
    if name.lower() in {r.value for r in Role} | {"agent", "system", "customer service"}:
        raise HTTPException(422, "approved_by must be the name of a person, not an agent")
    if view.run_status == "running":
        raise HTTPException(409, "Agents are still working on this ticket")
    if not view.awaiting_approval:
        raise HTTPException(409, f"Ticket {ticket_id} is {view.status!r}; nothing is waiting for a decision")
    if view.pending_payment and not view.pending_payment.already_paid:
        raise HTTPException(409, "This ticket has a payment to approve; use approve-payment")
    await mcp("add_ticket_note", ticket_id=ticket_id, actor="dashboard",
              note=f"Team recommendation accepted by {name}.")
    await mcp("update_ticket_status", ticket_id=ticket_id, status="resolved", actor="dashboard",
              note=f"Resolved by {name}.")
    return {"ticket_status": "resolved"}


# --------------------------------------------------------------------------- 5. cash
@app.get("/api/cash")
async def get_cash():
    """Current checking balance (and every account) from cash_accounts."""
    data = await mcp("list_cash_accounts")
    checking = next((a for a in data["accounts"] if a["name"] == "checking"), None)
    if checking is None:
        raise HTTPException(404, "No account named 'checking' in cash_accounts")
    return {"checking": checking["balance"], "as_of": checking["date"], **data}


# --------------------------------------------------------------------------- 6. reset
@app.post("/api/reset")
async def reset_database():
    """Restore the working database from the untouched original for a fresh run. The audit trail is NOT cleared."""
    global runs
    if active_run is not None:
        raise HTTPException(409, "An agent run is in progress; wait for it to finish before resetting")
    src, dst = sqlite3.connect(f"file:{ORIGINAL_DB}?mode=ro", uri=True), sqlite3.connect(WORKING_DB)
    try:
        src.backup(dst)               # safe even if the MCP server has the file open
    finally:
        src.close(); dst.close()
    runs = {}
    return {"reset": True, "restored_from": "data/campus_customs.db", "working_copy": "data/campus_customs_new.db",
            "audit_trail": "kept (append-only)", "cash": await get_cash()}
