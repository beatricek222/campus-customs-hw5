"""All data types for the Campus Customs agent team.

Three groups:
  * Role / limits / deps   - how the team is wired and what a run may spend.
  * Agent outputs          - the structured reports the agents must return.
  * AuditEntry             - one row of output/audit_trail.json.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_ai.usage import RunUsage

MODEL_NAME = "gpt-6-luna"  # the ONLY model any agent may use


# --------------------------------------------------------------------------- team wiring
class Role(str, Enum):
    BOSS = "boss"
    INVENTORY = "inventory"
    ACCOUNTING = "accounting"
    FACILITIES = "facilities"
    CUSTOMER_SERVICE = "customer_service"


ROLE_DESCRIPTIONS: dict[Role, str] = {
    Role.BOSS: "Triages the ticket queue, delegates to specialists, resolves conflicts between them (e.g. cash vs. "
               "customer promises) and returns the final plan. Ask the Boss only for a decision or a priority call.",
    Role.INVENTORY: "Owns stock levels, locations, pricing facts, margin math and vendor lead times for reorders. "
                    "Ask it whether an item/size/quantity can be filled, how short we are, and what a price does to margin.",
    Role.ACCOUNTING: "Owns cash, invoices, vendor payments and rent payments. Ask it whether something is affordable, "
                     "what is overdue, and to record an approved payment.",
    Role.FACILITIES: "Owns leases, landlords and rent due dates. Ask it to verify a rent notice against the lease "
                     "and to say how many days remain.",
    Role.CUSTOMER_SERVICE: "Owns everything customer-facing: reads the request, drafts replies, never promises what "
                           "stock, cash or approvals cannot back. Ask it to draft or check customer wording.",
}


class RunLimits(BaseModel):
    """Token / loop budget shared by a whole delegation tree (one Boss run and every nested call)."""
    max_depth: int = 3                    # Boss -> specialist -> specialist
    max_delegations: int = 12             # total ask_* calls in one tree
    request_limit: int = 60               # model round-trips, whole tree
    tool_calls_limit: int = 120           # tool calls, whole tree
    total_tokens_limit: int = 250_000     # input + output tokens, whole tree


@dataclass
class DelegationCounter:
    """Mutable counter shared by every run in one tree."""
    count: int = 0


@dataclass
class ShopDeps:
    """Dependencies handed to every agent run (and copied, one level deeper, to nested runs)."""
    root_run_id: str
    run_id: str
    parent_run_id: str | None
    depth: int
    chain: tuple[str, ...]                # roles currently waiting on each other, outermost first
    limits: RunLimits
    usage: RunUsage                       # shared across the tree so limits cover everything
    counter: DelegationCounter
    approved_by: str | None = None        # NAME OF A HUMAN who approved spending for this run; None = no approval


# --------------------------------------------------------------------------- agent outputs
class ApprovalRequest(BaseModel):
    """Something only a human may approve (money out, discounts, promises beyond the data)."""
    kind: Literal["payment", "discount", "reorder", "customer_promise", "other"]
    ticket_id: int | None = None
    summary: str = Field(description="One sentence a human can approve or reject.")
    amount: float | None = Field(default=None, description="Dollar amount, if money is involved.")
    recommended_action: str


class AgentReport(BaseModel):
    """What every specialist (and any agent delegated to) returns."""
    role: Role
    ticket_id: int | None = None
    summary: str = Field(description="2-4 sentences: the answer and the reason.")
    findings: list[str] = Field(default_factory=list, description="Facts read from the database, with the numbers.")
    actions_taken: list[str] = Field(default_factory=list, description="State changes actually made via tools.")
    recommendations: list[str] = Field(default_factory=list)
    approvals_needed: list[ApprovalRequest] = Field(default_factory=list)
    delegated_to: list[Role] = Field(default_factory=list)
    ticket_status_after: str | None = None
    customer_message: str | None = Field(default=None, description="DRAFT reply for a human to send; customer-safe wording only.")
    open_questions: list[str] = Field(default_factory=list)


class TicketOutcome(BaseModel):
    ticket_id: int
    decision: str = Field(description="What the shop will do about this ticket.")
    reasons: list[str]
    status_set: str | None = None
    next_steps: list[str] = Field(default_factory=list)


class BossReport(BaseModel):
    """Final output of a Boss run."""
    date_today: str
    summary: str
    ticket_outcomes: list[TicketOutcome]
    cash_plan: str = Field(description="How limited cash is allocated across payments, with numbers.")
    approvals_needed: list[ApprovalRequest] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- audit
AuditEvent = Literal["run_start", "user_prompt", "model_request", "model_response", "run_end", "run_error"]


class AuditEntry(BaseModel):
    """One appended row of output/audit_trail.json. Enough to replay who did what, why, and what it cost."""
    entry_id: str
    timestamp: str                         # UTC ISO-8601 (audit clock only; shop logic uses desk.date_today)
    root_run_id: str
    run_id: str
    parent_run_id: str | None
    depth: int
    agent: str
    model: str
    step: int                              # 0-based index inside this run
    event: AuditEvent
    details: dict[str, Any] = Field(default_factory=dict)
    usage_so_far: dict[str, int] = Field(default_factory=dict)   # tree-wide usage when the entry was written


# --------------------------------------------------------------------------- web API (backend/main.py)
class PendingPayment(BaseModel):
    """The one payment a ticket is linked to, as stored in the database (never typed in by the client)."""
    kind: Literal["invoice", "rent"]
    ref_id: int
    amount: float
    payee: str
    due_date: str
    already_paid: bool


class TicketView(BaseModel):
    id: int
    type: str
    requester: str
    subject: str
    sku: str | None = None
    size: str | None = None
    qty: int | None = None
    status: str                                # raw status: open, in_progress, waiting_approval, escalated, resolved
    state: Literal["open", "resolved"]         # what the board shows
    awaiting_approval: bool                    # agents prepared something and a human must act
    notes: str | None = None
    created_at: str
    pending_payment: PendingPayment | None = None
    run_status: Literal["idle", "running"] = "idle"
    last_run_id: str | None = None             # most recent agent run on this ticket (this server session)


class RunStatus(BaseModel):
    run_id: str
    ticket_id: int
    status: Literal["running", "done", "error"]
    started_at: str
    finished_at: str | None = None
    result: dict[str, Any] | None = None       # the Boss's BossReport once done
    error: str | None = None


class ApprovePaymentRequest(BaseModel):
    approved_by: str = Field(min_length=1, description="Full name of the person who clicked Approve.")
    account: str | None = Field(default=None, description="Cash account to pay from; optional when there is only one.")


class ResolveTicketRequest(BaseModel):
    approved_by: str = Field(min_length=1, description="Full name of the person accepting the team's recommendation.")


class AgentEvent(BaseModel):
    """A compact, board-friendly view of one audit entry."""
    index: int                                 # position in output/audit_trail.json (stable, append-only)
    timestamp: str
    root_run_id: str
    run_id: str
    parent_run_id: str | None
    depth: int
    agent: str
    step: int
    event: str
    task: str | None = None                    # what the agent was asked (run_start)
    said: str | None = None                    # what the agent said (text or its final summary)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)    # tools it called (and delegations)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)  # what the tools returned
    error: str | None = None
    output: dict[str, Any] | None = None       # the agent's full structured report (run_end only)
    usage: dict[str, int] = Field(default_factory=dict)
