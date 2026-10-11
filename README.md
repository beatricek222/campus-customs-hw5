# Campus Customs: an AI agent team that works the shop's tickets

Five AI agents (Boss, Inventory, Accounting, Facilities, Customer Service) work the open tickets of a small campus merchandise shop. They read and write shop data **only through an MCP server**, they can **only prepare** payments, and a **person approves** any money that moves from a React dashboard. Every agent step is appended to `output/audit_trail.json`.

All agents use one model, `gpt-6-luna`, through Portkey.

## What is in this repo

| Path | What it is |
|---|---|
| `data/campus_customs.db` | The **original** database (never modified by the app). |
| `data/campus_customs_new.db` | The **working copy** the app reads and writes. |
| `mcp_server/` | The FastMCP server (23 tools) over the working copy. See `mcp_server/README.md`. |
| `.mcp.json` | How the agents and the API connect to the MCP server. |
| `backend/` | FastAPI routes (`main.py`), data types (`models.py`), the five agents, and their prompts in `backend/prompts/`. |
| `frontend/` | React + Vite + TypeScript dashboard. |
| `output/` | Write-ups and evidence: `harness.md`, `design.md`, `desk_tickets.html` (Expected, Actual, Cash, Reflection), `resolved_tickets.json`, `resolved_board.html`, `audit_trail.json`, `mcp_smoke.json`, `github_url.txt`. |
| `AI_prompts.md` | The log of the prompts used to build this. |

## 1. One-time setup

You need Python 3.10+, Node.js 18+ and a Portkey API key.

```bash
# from the repo root
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env        # then edit .env and set PORTKEY_API_KEY
cd frontend && npm install && cd ..
```

`.mcp.json` points at `.venv/bin/python`, so create the virtual environment at the repo root with that exact name.

## 2. Get a clean database (original to working copy)

The app only changes `data/campus_customs_new.db`. Whenever you want a clean run, copy the original over it:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

Start of a clean run: checking balance **$3,400.00**, three open tickets (101, 102, 103), no payments. The copy in this repo is the state *after* the recorded run (balance $160.00, tickets resolved), so reset it before running the tickets yourself.

## 3. Start the MCP server

The backend and the agents start the MCP server for you through `.mcp.json`, so you normally do not have to. To run or inspect it on its own (it speaks MCP over stdio):

```bash
.venv/bin/python mcp_server/server.py
```

## 4. Start the FastAPI backend

```bash
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

The API is at http://localhost:8000 (interactive docs at http://localhost:8000/docs). Routes:

| Route | What it does |
|---|---|
| `GET /api/tickets` | Tickets with status, open or resolved, and any payment awaiting approval. |
| `POST /api/tickets/{id}/run` | Runs the agent team (Boss first) on one ticket in the background. |
| `GET /api/runs/{run_id}` | Status and final report of a run. |
| `GET /api/events` | Recent agent events: what each agent said, which tools it used. |
| `POST /api/tickets/{id}/approve-payment` | Pays the invoice or rent linked to a ticket, only after a person approves. |
| `POST /api/tickets/{id}/resolve` | A person accepts the team's recommendation when no payment is involved. |
| `GET /api/cash` | Current checking balance. |
| `POST /api/reset` | Restores the working database from the original. |

## 5. Start the React dashboard

In a second terminal:

```bash
cd frontend
npm run dev
```

It opens http://localhost:5173 and talks to the backend at http://localhost:8000 (the backend allows that origin through CORS). Pick a ticket, press **Run team**, watch the agents, then approve the payment or recommendation when the card appears.

## 6. Reset the database before a full 3-ticket run

Do one of these so you start from $3,400.00 with three open tickets:

- Click **Reset desk** on the dashboard, or
- `curl -X POST http://localhost:8000/api/reset` (backend running), or
- stop the app and `cp data/campus_customs.db data/campus_customs_new.db`.

Then run tickets 101, 102 and 103 from the dashboard. Each run ends at `waiting_approval`. Approving payment for 101 ($840 to Bulldog Print Co) and 102 ($2,400 rent) takes checking to $160.00; ticket 103 (a discount decision) needs a person to accept the recommendation and moves no cash.

Reset does not clear `output/audit_trail.json`: it is append-only on purpose.

## Safety in one paragraph

Agents have no way to pay: `record_payment` needs a named human approver and only the dashboard's approve route supplies one. Payments must equal the amount due, cannot overdraw the account, and cannot be repeated. Prices never go below unit cost, agents never send messages to customers, ticket text is treated as data and not instructions, and each role can call only the MCP tools listed for it. The full list is in `output/harness.md`.

## Secrets

`.env` is git-ignored; only `.env.example` is committed. Put your own `PORTKEY_API_KEY` in `.env`.
