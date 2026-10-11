# Campus Customs MCP Server

## What it is for
The only way the Campus Customs agents (Boss, Inventory, Accounting, Facilities, Customer Service) read or change shop data. Tools return only what is stored in the database (or arithmetic on it) and never invent anything; there is no other shop-data layer.

## Database
`data/campus_customs_new.db` (the working copy). The original `data/campus_customs.db` is never opened. Reads are read-only; write tools run in a single transaction with guardrails.

## Tools (23)

**Original three**
| Tool | Tables | Returns |
|---|---|---|
| `get_stock(sku, size)` | `inventory` | Qty, name, location for one SKU and size |
| `get_lease_due(lease_id)` | `leases`, `desk` | Rent, landlord, due date, days until due |
| `get_pricing(sku)` | `pricing` | Unit cost, list price, margin per unit |

**Read tools**
| Tool | Tables | Returns |
|---|---|---|
| `get_today()` | `desk` | Business date and desk notes |
| `list_tickets(status?)` | `tickets` | The ticket queue |
| `get_ticket(ticket_id)` | `tickets` | One ticket |
| `get_ticket_context(ticket_id)` | `tickets`, `desk`, `inventory`, `pricing`, `leases`, `invoices`, `vendors`, `payments`, `cash_accounts` | A ticket plus every record it links to |
| `list_inventory(sku?)` | `inventory` | Stock rows |
| `list_stock_at_or_below(max_qty)` | `inventory` | Items at or below a caller-chosen quantity |
| `list_pricing()` | `pricing` | Cost, list price, margin for every SKU |
| `quote_order(sku, size, qty, proposed_unit_price?)` | `inventory`, `pricing` | Shortfall, totals, margin, discount %, below-cost flag |
| `list_vendors()` | `vendors` | All vendors and lead times |
| `find_vendors(keyword)` | `vendors` | Vendors whose name or specialty match |
| `list_invoices(status?)` | `invoices`, `vendors`, `desk` | Invoices with vendor and days overdue |
| `get_invoice(invoice_id)` | `invoices`, `vendors`, `payments`, `desk` | One invoice with vendor, overdue days and payments |
| `list_leases()` | `leases`, `desk` | Leases with days until due |
| `list_cash_accounts()` | `cash_accounts` | Balances and total |
| `list_payments(kind?, ref_id?)` | `payments` | Recorded payments |
| `get_cash_outlook(days_ahead)` | `desk`, `cash_accounts`, `invoices`, `vendors`, `leases` | Balance, obligations due in the window, projected balance |

**Write tools** (working copy only)
| Tool | Tables | Does |
|---|---|---|
| `add_ticket_note(ticket_id, actor, note)` | `tickets`, `desk` | Appends a dated, attributed note |
| `update_ticket_status(ticket_id, status, actor, note)` | `tickets`, `desk` | Sets status (open, in_progress, waiting_approval, escalated, resolved) with a reason |
| `adjust_inventory(sku, size, delta, actor, reason)` | `inventory` | Changes stock; refuses negatives |
| `record_payment(kind, ref_id, amount, account, approved_by, actor)` | `payments`, `cash_accounts`, `invoices`, `leases`, `desk` | Pays an open invoice or a lease's rent; needs a human `approved_by`, exact amount, enough cash; no double pay |

## Running
Connected through `.mcp.json` (uses the project's `.venv`). Standalone: `.venv/bin/python mcp_server/server.py`.
