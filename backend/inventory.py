"""INVENTORY agent: stock, locations, pricing facts, margin math, vendor lead times, stock adjustments."""
from .models import Role
from .runtime import build_agent

ROLE = Role.INVENTORY

TOOLS = {
    "get_today", "get_ticket", "get_ticket_context", "get_stock", "list_inventory", "list_stock_at_or_below",
    "get_pricing", "list_pricing", "quote_order", "list_vendors", "find_vendors",
    "adjust_inventory", "add_ticket_note",
}

agent = build_agent(ROLE, tools_allowed=TOOLS)
