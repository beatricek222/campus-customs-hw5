"""ACCOUNTING agent: cash, invoices, vendor payments, rent payments. The only role allowed to record a payment."""
from .models import Role
from .runtime import build_agent

ROLE = Role.ACCOUNTING

TOOLS = {
    "get_today", "get_ticket", "get_ticket_context", "list_cash_accounts", "get_cash_outlook",
    "list_invoices", "get_invoice", "list_leases", "get_lease_due", "list_payments",
    "list_vendors", "record_payment", "add_ticket_note", "update_ticket_status",
}

agent = build_agent(ROLE, tools_allowed=TOOLS)
