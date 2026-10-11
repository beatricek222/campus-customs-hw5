"""Campus Customs MCP server (FastMCP).

This is the ONLY layer the agents use to touch shop data. Every tool reads from
or writes to data/campus_customs_new.db (the working copy; the original
data/campus_customs.db is never opened). Tools return only values stored in the
database, or values computed from them, and return an {"error": ...} dict when
a record is missing or a rule is broken. Nothing is guessed or invented.

Read tools open the database read-only. Write tools run inside one transaction
and enforce hard guardrails (no overdraft, no negative stock, no paying the
same invoice twice, a human approver is required for any payment).
"""
import calendar
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path

from fastmcp import FastMCP

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus_customs_new.db"

TICKET_STATUSES = ("open", "in_progress", "waiting_approval", "escalated", "resolved")
AGENT_NAMES = ("boss", "inventory", "accounting", "facilities", "customer_service", "customer service", "agent", "system")

mcp = FastMCP("campus-customs")


# --------------------------------------------------------------------------- helpers
def _query(sql: str, params: tuple = ()) -> list[dict]:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


@contextmanager
def _write_conn():
    """One read-write transaction; commits on success and rolls back on error."""
    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def _today() -> str | None:
    rows = _query("SELECT date_today FROM desk LIMIT 1")
    return rows[0]["date_today"] if rows else None


def _add_month(d: date) -> date:
    y, m = (d.year + 1, 1) if d.month == 12 else (d.year, d.month + 1)
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def _bad_actor(name: str) -> str | None:
    return None if name and name.strip() else "actor is required so the change can be audited"


# --------------------------------------------------------------------------- original 3 read tools
@mcp.tool()
def get_stock(sku: str, size: str) -> dict:
    """Return on-hand quantity and shelf location for one SKU in one size.

    Used for ticket 101 (is CC-TEE-WHITE size S in stock?).
    """
    rows = _query(
        "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ?",
        (sku, size),
    )
    if not rows:
        return {"error": f"No inventory row for sku={sku!r}, size={size!r}"}
    return rows[0]


@mcp.tool()
def get_lease_due(lease_id: int) -> dict:
    """Return a lease's rent, landlord and due date, plus days until due
    counted from the desk's date_today (negative means overdue).

    Used for ticket 102 (Chapel Street shop rent).
    """
    leases = _query(
        "SELECT id, space_name, landlord, monthly_rent, next_due, notes FROM leases WHERE id = ?",
        (lease_id,),
    )
    if not leases:
        return {"error": f"No lease with id={lease_id}"}
    today = _today()
    if not today:
        return {"error": "desk.date_today is not set", **leases[0]}
    days = (date.fromisoformat(leases[0]["next_due"]) - date.fromisoformat(today)).days
    return {**leases[0], "date_today": today, "days_until_due": days}


@mcp.tool()
def get_pricing(sku: str) -> dict:
    """Return unit cost, list price and per-unit margin for a SKU.

    Used for ticket 103 (how far can the hoodie price be discounted?).
    """
    rows = _query("SELECT sku, unit_cost, list_price FROM pricing WHERE sku = ?", (sku,))
    if not rows:
        return {"error": f"No pricing row for sku={sku!r}"}
    row = rows[0]
    row["margin_per_unit"] = round(row["list_price"] - row["unit_cost"], 2)
    return row


# --------------------------------------------------------------------------- new read tools: desk and tickets
@mcp.tool()
def get_today() -> dict:
    """Return the shop's current business date and any desk notes (table: desk).

    Agents must use this date, never the system clock, for due-date judgments.
    """
    rows = _query("SELECT date_today, notes FROM desk LIMIT 1")
    return rows[0] if rows else {"error": "desk table is empty"}


@mcp.tool()
def list_tickets(status: str | None = None) -> dict:
    """List tickets (table: tickets), optionally only those with the given status.

    Used by the Boss to see the whole queue (101 customer order, 102 rent notice,
    103 price override) before delegating.
    """
    if status:
        rows = _query("SELECT * FROM tickets WHERE status = ? ORDER BY id", (status,))
    else:
        rows = _query("SELECT * FROM tickets ORDER BY id")
    return {"count": len(rows), "tickets": rows}


@mcp.tool()
def get_ticket(ticket_id: int) -> dict:
    """Return one ticket row exactly as stored (table: tickets)."""
    rows = _query("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    return rows[0] if rows else {"error": f"No ticket with id={ticket_id}"}


@mcp.tool()
def get_ticket_context(ticket_id: int) -> dict:
    """Return a ticket together with every record it links to, in one call.

    Tables: tickets, desk, inventory, pricing, leases, invoices, vendors,
    cash_accounts, payments. For 101 this brings the S tee stock, invoice 501
    and its vendor; for 102 the lease and the checking balance; for 103 the
    M hoodie stock and pricing. Only linked rows are returned; nothing is inferred.
    """
    t = _query("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    if not t:
        return {"error": f"No ticket with id={ticket_id}"}
    t = t[0]
    ctx: dict = {"ticket": t, "date_today": _today()}
    if t["sku"]:
        if t["size"]:
            ctx["inventory"] = _query("SELECT * FROM inventory WHERE sku = ? AND size = ?", (t["sku"], t["size"]))
        else:
            ctx["inventory"] = _query("SELECT * FROM inventory WHERE sku = ?", (t["sku"],))
        ctx["pricing"] = _query("SELECT * FROM pricing WHERE sku = ?", (t["sku"],))
    if t["lease_id"] is not None:
        ctx["lease"] = _query("SELECT * FROM leases WHERE id = ?", (t["lease_id"],))
        ctx["payments_for_lease"] = _query(
            "SELECT * FROM payments WHERE kind = 'rent' AND ref_id = ?", (t["lease_id"],))
    if t["invoice_id"] is not None:
        ctx["invoice"] = _query("SELECT * FROM invoices WHERE id = ?", (t["invoice_id"],))
        if ctx["invoice"]:
            ctx["vendor"] = _query("SELECT * FROM vendors WHERE id = ?", (ctx["invoice"][0]["vendor_id"],))
        ctx["payments_for_invoice"] = _query(
            "SELECT * FROM payments WHERE kind = 'invoice' AND ref_id = ?", (t["invoice_id"],))
    ctx["cash_accounts"] = _query("SELECT * FROM cash_accounts")
    return ctx


# --------------------------------------------------------------------------- new read tools: inventory, pricing, vendors
@mcp.tool()
def list_inventory(sku: str | None = None) -> dict:
    """List stock rows (table: inventory), for one SKU or for the whole shop."""
    if sku:
        rows = _query("SELECT * FROM inventory WHERE sku = ? ORDER BY sku, size", (sku,))
    else:
        rows = _query("SELECT * FROM inventory ORDER BY sku, size")
    return {"count": len(rows), "rows": rows}


@mcp.tool()
def list_stock_at_or_below(max_qty: int) -> dict:
    """List every (sku, size) whose on-hand qty is at or below max_qty (table: inventory).

    The caller chooses max_qty (use 0 for stock-outs); no threshold is assumed here.
    """
    rows = _query("SELECT * FROM inventory WHERE qty <= ? ORDER BY qty, sku, size", (max_qty,))
    return {"max_qty": max_qty, "count": len(rows), "rows": rows}


@mcp.tool()
def list_pricing() -> dict:
    """List unit cost, list price and margin for every SKU (table: pricing)."""
    rows = _query("SELECT sku, unit_cost, list_price FROM pricing ORDER BY sku")
    for r in rows:
        r["margin_per_unit"] = round(r["list_price"] - r["unit_cost"], 2)
    return {"count": len(rows), "rows": rows}


@mcp.tool()
def quote_order(sku: str, size: str, qty: int, proposed_unit_price: float | None = None) -> dict:
    """Price and stock-check an order line (tables: inventory, pricing).

    Returns stock on hand, any shortfall, list price, unit cost, line totals and
    margin. If proposed_unit_price is given it also returns the discount versus
    list and flags whether the price is below cost. Used for ticket 103
    (20 x CC-HOOD-NAVY size M) and ticket 101 (1 x CC-TEE-WHITE size S).
    """
    if qty <= 0:
        return {"error": "qty must be positive"}
    inv = _query("SELECT * FROM inventory WHERE sku = ? AND size = ?", (sku, size))
    pr = _query("SELECT * FROM pricing WHERE sku = ?", (sku,))
    if not inv:
        return {"error": f"No inventory row for sku={sku!r}, size={size!r}"}
    if not pr:
        return {"error": f"No pricing row for sku={sku!r}"}
    on_hand, cost, lst = inv[0]["qty"], pr[0]["unit_cost"], pr[0]["list_price"]
    out = {
        "sku": sku, "size": size, "qty_requested": qty, "qty_on_hand": on_hand,
        "shortfall": max(qty - on_hand, 0), "can_fill_from_stock": on_hand >= qty,
        "unit_cost": cost, "list_price": lst,
        "line_total_at_list": round(lst * qty, 2), "line_cost": round(cost * qty, 2),
        "line_margin_at_list": round((lst - cost) * qty, 2),
    }
    if proposed_unit_price is not None:
        p = proposed_unit_price
        out.update({
            "proposed_unit_price": p,
            "discount_vs_list_pct": round((lst - p) / lst * 100, 2),
            "line_total_at_proposed": round(p * qty, 2),
            "line_margin_at_proposed": round((p - cost) * qty, 2),
            "margin_pct_at_proposed": round((p - cost) / p * 100, 2) if p > 0 else None,
            "below_cost": p < cost,
        })
    return out


@mcp.tool()
def list_vendors() -> dict:
    """List all vendors with specialty and lead time (table: vendors)."""
    rows = _query("SELECT * FROM vendors ORDER BY id")
    return {"count": len(rows), "vendors": rows}


@mcp.tool()
def find_vendors(keyword: str) -> dict:
    """Find vendors whose specialty or name contains the keyword (table: vendors).

    Example: 'reprint' finds Bulldog Print Co (lead_days 5). The database does not
    map SKUs to vendors, so the caller must say that any match is an inference.
    """
    like = f"%{keyword}%"
    rows = _query("SELECT * FROM vendors WHERE specialty LIKE ? OR name LIKE ? ORDER BY id", (like, like))
    return {"keyword": keyword, "count": len(rows), "vendors": rows}


# --------------------------------------------------------------------------- new read tools: money
@mcp.tool()
def list_invoices(status: str | None = None) -> dict:
    """List invoices with vendor name and days overdue (tables: invoices, vendors, desk).

    days_overdue is today minus due_date; positive means overdue, negative means not yet due.
    """
    sql = ("SELECT i.*, v.name AS vendor_name, v.specialty AS vendor_specialty, v.lead_days AS vendor_lead_days "
           "FROM invoices i JOIN vendors v ON v.id = i.vendor_id")
    rows = _query(sql + (" WHERE i.status = ? ORDER BY i.id" if status else " ORDER BY i.id"),
                  (status,) if status else ())
    today = _today()
    for r in rows:
        r["days_overdue"] = (date.fromisoformat(today) - date.fromisoformat(r["due_date"])).days if today else None
    return {"date_today": today, "count": len(rows), "invoices": rows}


@mcp.tool()
def get_invoice(invoice_id: int) -> dict:
    """Return one invoice with its vendor and days overdue (tables: invoices, vendors, desk, payments)."""
    rows = _query(
        "SELECT i.*, v.name AS vendor_name, v.specialty AS vendor_specialty, v.lead_days AS vendor_lead_days "
        "FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?", (invoice_id,))
    if not rows:
        return {"error": f"No invoice with id={invoice_id}"}
    r = rows[0]
    today = _today()
    r["date_today"] = today
    r["days_overdue"] = (date.fromisoformat(today) - date.fromisoformat(r["due_date"])).days if today else None
    r["payments"] = _query("SELECT * FROM payments WHERE kind = 'invoice' AND ref_id = ?", (invoice_id,))
    return r


@mcp.tool()
def list_leases() -> dict:
    """List every lease with days until the next rent due date (tables: leases, desk)."""
    rows = _query("SELECT * FROM leases ORDER BY id")
    today = _today()
    for r in rows:
        r["days_until_due"] = (date.fromisoformat(r["next_due"]) - date.fromisoformat(today)).days if today else None
    return {"date_today": today, "count": len(rows), "leases": rows}


@mcp.tool()
def list_cash_accounts() -> dict:
    """List cash accounts with balance and as-of date (table: cash_accounts)."""
    rows = _query("SELECT * FROM cash_accounts ORDER BY name")
    return {"count": len(rows), "accounts": rows, "total_balance": round(sum(r["balance"] for r in rows), 2)}


@mcp.tool()
def list_payments(kind: str | None = None, ref_id: int | None = None) -> dict:
    """List recorded payments, optionally by kind ('invoice' or 'rent') and ref_id (table: payments).

    Always check this before paying anything, to avoid paying the same item twice.
    """
    sql, params, where = "SELECT * FROM payments", [], []
    if kind:
        where.append("kind = ?"); params.append(kind)
    if ref_id is not None:
        where.append("ref_id = ?"); params.append(ref_id)
    rows = _query(sql + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id", tuple(params))
    return {"count": len(rows), "payments": rows}


@mcp.tool()
def get_cash_outlook(days_ahead: int) -> dict:
    """Project cash after every unpaid obligation due within days_ahead of today.

    Tables: desk, cash_accounts, invoices, leases, vendors. Obligations are all
    open invoices due on or before today+days_ahead (overdue ones included) and
    all leases whose next_due falls on or before that date. It is arithmetic on
    stored values only; it does not forecast sales.
    """
    today = _today()
    if not today:
        return {"error": "desk.date_today is not set"}
    horizon = (date.fromisoformat(today) + timedelta(days=days_ahead)).isoformat()
    balance = sum(r["balance"] for r in _query("SELECT balance FROM cash_accounts"))
    invs = _query("SELECT i.id, v.name AS vendor_name, i.amount, i.due_date, i.status, i.description "
                  "FROM invoices i JOIN vendors v ON v.id = i.vendor_id "
                  "WHERE i.status = 'open' AND i.due_date <= ? ORDER BY i.due_date", (horizon,))
    leases = _query("SELECT id, space_name, landlord, monthly_rent AS amount, next_due AS due_date "
                    "FROM leases WHERE next_due <= ? ORDER BY next_due", (horizon,))
    total = round(sum(i["amount"] for i in invs) + sum(l["amount"] for l in leases), 2)
    return {"date_today": today, "horizon_date": horizon, "cash_balance": round(balance, 2),
            "open_invoices_due": invs, "leases_due": leases, "total_obligations": total,
            "projected_balance_after_all": round(balance - total, 2),
            "shortfall": round(max(total - balance, 0), 2)}


# --------------------------------------------------------------------------- write tools (working copy only)
@mcp.tool()
def add_ticket_note(ticket_id: int, actor: str, note: str) -> dict:
    """Append a dated, attributed note to a ticket's notes field (table: tickets). Never overwrites old text."""
    if (e := _bad_actor(actor)) or not note.strip():
        return {"error": e or "note is empty"}
    today = _today()
    with _write_conn() as c:
        row = c.execute("SELECT notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if not row:
            return {"error": f"No ticket with id={ticket_id}"}
        new = ((row["notes"] + "\n") if row["notes"] else "") + f"[{today}] {actor}: {note.strip()}"
        c.execute("UPDATE tickets SET notes = ? WHERE id = ?", (new, ticket_id))
    return {"ticket_id": ticket_id, "notes": new}


@mcp.tool()
def update_ticket_status(ticket_id: int, status: str, actor: str, note: str) -> dict:
    """Set a ticket's status and append the reason as a note (table: tickets).

    Allowed statuses: open, in_progress, waiting_approval, escalated, resolved.
    Use waiting_approval when a human must approve money or a discount.
    """
    if status not in TICKET_STATUSES:
        return {"error": f"status must be one of {TICKET_STATUSES}"}
    if (e := _bad_actor(actor)) or not note.strip():
        return {"error": e or "a reason note is required"}
    today = _today()
    with _write_conn() as c:
        row = c.execute("SELECT status, notes FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if not row:
            return {"error": f"No ticket with id={ticket_id}"}
        new = ((row["notes"] + "\n") if row["notes"] else "") + \
            f"[{today}] {actor}: status {row['status']} -> {status}. {note.strip()}"
        c.execute("UPDATE tickets SET status = ?, notes = ? WHERE id = ?", (status, new, ticket_id))
    return {"ticket_id": ticket_id, "old_status": row["status"], "new_status": status}


@mcp.tool()
def adjust_inventory(sku: str, size: str, delta: int, actor: str, reason: str) -> dict:
    """Add (positive) or remove (negative) units for one SKU and size (table: inventory).

    Refuses to take stock below zero or to touch a row that does not exist.
    Use for received shipments and for units physically handed to a customer.
    """
    if (e := _bad_actor(actor)) or not reason.strip():
        return {"error": e or "reason is required"}
    if delta == 0:
        return {"error": "delta must not be 0"}
    with _write_conn() as c:
        row = c.execute("SELECT qty FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone()
        if not row:
            return {"error": f"No inventory row for sku={sku!r}, size={size!r}"}
        new = row["qty"] + delta
        if new < 0:
            return {"error": f"Would make stock negative (on hand {row['qty']}, delta {delta})"}
        c.execute("UPDATE inventory SET qty = ? WHERE sku = ? AND size = ?", (new, sku, size))
    return {"sku": sku, "size": size, "old_qty": row["qty"], "new_qty": new, "actor": actor, "reason": reason}


@mcp.tool()
def record_payment(kind: str, ref_id: int, amount: float, account: str, approved_by: str, actor: str) -> dict:
    """Pay an open invoice (kind='invoice') or a lease's rent (kind='rent').

    Tables written: payments, cash_accounts, and invoices (status -> 'paid') or
    leases (next_due moves one month). Hard rules enforced here: approved_by must
    be a named human (agent names are rejected); the amount must equal the invoice
    amount or the lease's monthly_rent; the account must exist and cover it (no
    overdraft); an invoice already paid, or a lease with a rent payment recorded
    for the current next_due, cannot be paid again.
    """
    if kind not in ("invoice", "rent"):
        return {"error": "kind must be 'invoice' or 'rent'"}
    if not approved_by.strip() or approved_by.strip().lower() in AGENT_NAMES:
        return {"error": "approved_by must be the name of a human approver, not an agent"}
    if (e := _bad_actor(actor)):
        return {"error": e}
    today = _today()
    with _write_conn() as c:
        acct = c.execute("SELECT balance FROM cash_accounts WHERE name = ?", (account,)).fetchone()
        if not acct:
            return {"error": f"No cash account named {account!r}"}
        if kind == "invoice":
            inv = c.execute("SELECT amount, status FROM invoices WHERE id = ?", (ref_id,)).fetchone()
            if not inv:
                return {"error": f"No invoice with id={ref_id}"}
            if inv["status"] != "open":
                return {"error": f"Invoice {ref_id} is {inv['status']!r}, not open"}
            due_amount = inv["amount"]
        else:
            lease = c.execute("SELECT monthly_rent, next_due FROM leases WHERE id = ?", (ref_id,)).fetchone()
            if not lease:
                return {"error": f"No lease with id={ref_id}"}
            due_amount = lease["monthly_rent"]
            dup = c.execute("SELECT 1 FROM payments WHERE kind='rent' AND ref_id=? AND paid_at >= ?",
                            (ref_id, lease["next_due"][:7] + "-01")).fetchone()
            if dup:
                return {"error": f"Rent for lease {ref_id} already recorded for the period due {lease['next_due']}"}
        if abs(amount - due_amount) > 0.005:
            return {"error": f"amount {amount} does not equal the amount due {due_amount}"}
        if acct["balance"] < amount:
            return {"error": f"Insufficient funds: {account} has {acct['balance']}, payment is {amount}"}
        cur = c.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?,?,?,?,?,?)",
            (kind, ref_id, amount, account, today, f"{approved_by.strip()} (recorded by {actor})"))
        new_bal = round(acct["balance"] - amount, 2)
        c.execute("UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?", (new_bal, today, account))
        if kind == "invoice":
            c.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,))
        else:
            nxt = _add_month(date.fromisoformat(lease["next_due"])).isoformat()
            c.execute("UPDATE leases SET next_due = ? WHERE id = ?", (nxt, ref_id))
    return {"payment_id": cur.lastrowid, "kind": kind, "ref_id": ref_id, "amount": amount,
            "account": account, "new_balance": new_bal, "paid_at": today, "approved_by": approved_by}


if __name__ == "__main__":
    mcp.run()
