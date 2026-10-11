"""FACILITIES agent: leases, landlords, rent due dates; verifies rent notices against the lease record."""
from .models import Role
from .runtime import build_agent

ROLE = Role.FACILITIES

TOOLS = {
    "get_today", "get_ticket", "get_ticket_context", "list_leases", "get_lease_due",
    "list_payments", "get_cash_outlook", "add_ticket_note",
}

agent = build_agent(ROLE, tools_allowed=TOOLS)
