"""BOSS agent: triages the ticket queue, delegates to the four specialists, returns the final plan."""
from .models import BossReport, Role
from .runtime import build_agent

ROLE = Role.BOSS

# MCP tools this role may call (least privilege). The Boss reads broadly but changes only ticket status/notes;
# it never moves money or stock itself - it delegates to Accounting / Inventory.
TOOLS = {
    "get_today", "list_tickets", "get_ticket", "get_ticket_context", "list_stock_at_or_below",
    "quote_order", "list_invoices", "list_leases", "get_cash_outlook",
    "add_ticket_note", "update_ticket_status",
}

agent = build_agent(ROLE, tools_allowed=TOOLS, output_type=BossReport)
