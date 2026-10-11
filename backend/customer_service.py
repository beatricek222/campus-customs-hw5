"""CUSTOMER SERVICE agent: understands customer requests and drafts customer-safe replies (never sends, never promises)."""
from .models import Role
from .runtime import build_agent

ROLE = Role.CUSTOMER_SERVICE

TOOLS = {
    "get_today", "get_ticket", "get_ticket_context", "get_stock", "list_inventory", "get_pricing",
    "quote_order", "list_vendors", "find_vendors", "add_ticket_note", "update_ticket_status",
}

agent = build_agent(ROLE, tools_allowed=TOOLS)
