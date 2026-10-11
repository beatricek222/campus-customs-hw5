# AI Prompts Log

A running log of the prompts typed to Claude while working on this assignment, organized by problem.

---

## Problem 1: Vibe coder prompts

### Prompt 1

> Problem 1: Vibe coder prompts
>
> Create AI_prompts.md and keep it updated as we work, having it be the log of our chats and everything I typed to you. Make one section for each problem, where each section includes (1) the problem number and title, (2) at least one prompt that I typed, and (3) at least one followup prompt when applicable and a sentence on what was lacking in the first prompt.

**Outcome:** Claude created this file with the structure requested.

### Follow-up prompt(s)

_None yet. Any follow-up prompts for this problem will be added here, each with a sentence on what was lacking in the prompt before it._

**What was lacking in the first prompt:** _To be filled in once a follow-up is needed._

---

## Problem 2: Study the Campus Customs database

### Prompt 1

> Problem 2: Study the Campus Customs database
>
> Open and look through every table and all the fields in the database in data/campus_customs.db. There's also a copy of this database called data/campus_customs_new.db that later problems will update to have one working copy and one original database.
>
> Please pay attention to and study the 3 open tickets, such that you understand how they link to other tables.
>
> Also, please create output/harness.md. For every table of the database, list each field and write one line on why the tables is important for the agents. We will continue to grow this harness file in later problems.

**Outcome:** Claude read all 9 tables and wrote `output/harness.md` with every field, a one-line importance note per table, and a breakdown of how tickets 101, 102 and 103 link to inventory, pricing, vendors, invoices, leases and cash.

### Follow-up prompt(s)

_None yet._

**What was lacking in the first prompt:** _To be filled in once a follow-up is needed._

---

## Problem 3: Build the MCP server

### Prompt 1

> Problem 3: Build the MCP server
>
> Now, please write an MCP server in mcp_server/ using FastMCP, which should talk to data/campus_customs_new.db. We don't need to run it or connect it for now in this problem. Please note that every agent in this homework assignment uses tools in this MCP server.
>
> Please create and write 3 tools that you know we will need for the tickets in the database. We will also add some more tools later. Also please note that you should never invent any data and only use information that is in the database.
>
> Then, in output/harness.md, please write down each of the 3 MCP tools, and for each tool, write (1) which table it reads, (2) which ticket it helps unlock of the 3 (101, 102, or 103), and (3) ONE sentence on why you chose that particular tool and why the tool is the right one for that ticket. Please make the tool specific to the ticket, as vague lines such as "reads inventory" will score a low grade.
>
> Additionally, please make a concise mcp_server/README.md file that reflects on and explains (1) what the MCP server is for, (2) what database file the MCP server uses, and (3) the 3 tools that it contains.

**Outcome:** Claude wrote `mcp_server/server.py` with `get_stock`, `get_lease_due` and `get_pricing`, a short `mcp_server/README.md`, and an "MCP tools" section in `output/harness.md`.

### Follow-up prompt(s)

> Do you think get_stock is too vague? The assignment says that vague lines like 'reads inventory' score low and to tie the tool to the ticket

**Outcome:** Claude rewrote the `get_stock` entry in `output/harness.md` to name the exact row (`CC-TEE-WHITE`, size S), the qty 0 result, and the invoice 501 reprint.

> I think it's ok as is

**Outcome:** Kept the tool generic (it is also reusable for ticket 103); no code change.

> Did you make sure that there is a specific sentence on why that tool is right for that ticket?

**Outcome:** Claude confirmed each tool had a one-sentence "Why" and offered to reword the 102 and 103 lines to lead with the reason.

> Yes, please ADD exactly why it was chosen

**Outcome:** Claude rewrote all three "Why" lines in `output/harness.md` to start with "Chosen because...", stating the specific reason each tool fits its ticket.

**What was lacking in the first prompt:** It did not say that the harness lines must name the exact SKU, size, quantities and linked records for each ticket, so the first `get_stock` entry came out too generic.

---

## Problem 4: Add the MCP server to vibe coder and test each tool

### Prompt 1

> Problem 4: Add the MCP server to vibe coder and test each tool.
>
> First, make sure that FastMCP is installed, and if not, install it. Then, add the MCP server to this project such that the vibe coder (you) can call all the tools. In the project root in .mcp.json, please save the connection JSON text.
>
> Then, with the vibe coder connected, test each of the 3 MCP tools that we created in the last problem. Please save the evidence to output/mcp_smoke.json. For each of the 3 tools that you test, make sure to include (1) the prompt that was asked, (2) the tool name, and (3) the tool output, which must match the values in data/campus_customs_new.db

**Outcome:** Claude found FastMCP only partly installed (missing a dependency) and upgraded it to 4.1.0, wrote `.mcp.json`, and called all 3 tools over MCP stdio using that config. Results were checked against the database and saved to `output/mcp_smoke.json`.

### Follow-up prompt(s)

_None yet._

**What was lacking in the first prompt:** _To be filled in once a follow-up is needed._

---

## Problem 5: Build the agent team and grow the MCP tools

### Prompt 1

> Problem 5: Build the agent team and grow the MCP tools
>
> Now, please build out the agentic team for Campus Customs, with the following agents: Boss, Inventory, Accounting, Facilities, and Customer Service. Use PydanticAI for the agents. For each agent, please make sure to include prompts, models, and agent loops, such that the agents can delegate work to each other with full connectivity. Please put all the agent prompts in backend/prompts/ and make ONE file per agent (so 5 files total). Write all the data types in backend/models.py, and put the agent files in backend/ (make sure he 5 roles are clear). Please use my PORTKEY_API_KEY and ONLY use the gpt-6-luna model for each agent. Please let me know how to connect PORTKEY_API_KEY if it is not already connected.
>
> Please make sure to write and explain each prompt in an optimized, professional, very detailed manner with the shop rules that the agent needs. The prompt MUST be detailed and cover ALL aspects of an agent's scope and work (I get graded on the detailedness of this so make sure you are detailed).
>
> Then, please add any tools you see fit that the agents will need to the MCP server so that they can work on the open tickets. Don't be shy and add as many as you can think of that would be useful, but don't invent any data or facts. You can see shop facts from the MCP server over data/campus_customs_new.db. Please DON'T invent a second shop-tools layer that can bypass the MCP.
>
> All the agents should append to output/audit_trail.json as they run. Please make sure this happens. For each agent-loop step, record enough such that it can be audited later. Do not wipe things after each run, only append to this file.
>
> Additionally, in output/harness.md, write down each agent and each MCP tool (including the 3 that were added in a previous problem and all the ones that were added in this problem). For each tool, list which table(s) the tool uses. Please also add a concise Safety section that specifies the guardrails that a real business would want when agents work on real customers and money, as well as limits that keep token use in check.
>
> Then, please update mcp_server/README.md to reflect all the tools we have such that the tool list matches all the tools we now have.

**Outcome:** Claude built the five PydanticAI agents (`backend/boss.py`, `inventory.py`, `accounting.py`, `facilities.py`, `customer_service.py`) with one detailed prompt each in `backend/prompts/`, types in `backend/models.py`, shared runtime and audit writer, 20 new MCP tools (23 total), and updated `output/harness.md` and `mcp_server/README.md`.

### Follow-up prompt(s)

_None yet._

**What was lacking in the first prompt:** _To be filled in once a follow-up is needed._

---

## Problem 6: Plan the three tickets

### Prompt 1

> Problem 6: Plan the 3 tickets
>
> Before wiring the backend, please write down what you expect the team of agents to do for each open ticket. Create output/desk_tickets.html as a page where someone can double-click with one tab per ticket for the tickets 101 , 102, and 103. Add empty Cash and Reflection tabs as well for later problems, but leave them blank for now. In each ticket tab, fill in only the Expected section (you will fill in the Actual section when you actually run the agents).
>
> For the Expected section for each ticket, write and explain (1) who the boss should call first and why, (2) all the agent delegations that you would expect (be specific, don't just say "Boss calls everyone"), and (3) which MCP tools you expect the run to use. Do not send every specialist on every ticket, as this will get me a bad grade. Please be selective while still accomplishing the task. You will later compare this plan to what actually happens when the agents resolve the tickets.

**Outcome:** Claude created `output/desk_tickets.html`, a standalone page with tabs for 101, 102, 103, Cash and Reflection. Each ticket tab has a filled Expected section (first call, delegations, tools, outcome) and an empty Actual section; Cash and Reflection are blank.

### Follow-up prompt(s)

_None yet._

**What was lacking in the first prompt:** _To be filled in once a follow-up is needed._

---

## Problem 7: Backend routes

### Prompt 1

> Problem 7: Backend routes
>
> We will be building the React frontend dashboard in the next problem, and it needs a backend that it can call. Use FastAPI to add routes to backend/main.py that do the following things: (1) Return the 3 tickets and if each is open or resolved, (2) Take a ticket id and run the agent team on that ticket, (3) Return recent agent events, including what each agent said and what tools they used, such that the board can refresh, (4) Approve a payment or purchase ONLY after a person clicks approve (the agents only prepare the pay, but this route is what actually changes the cash), (5) Check and return the current checking balance from cash_accounts, (6) Reset the database to the original values when we want to try a fresh run.
>
> Start the server with the following command from the backend folder, which turns on the backend at http://localhost:8000, such that the frontend dashboard can call the created routes: uvicorn main:app --reload --port 8000
>
> Also, in output/harness.md, please explain each route (both the URL AND what it does) in one line.

**Outcome:** Claude added the FastAPI routes to `backend/main.py` (the old command-line runner moved to `backend/cli.py`), plus a run-status route, added the API types to `backend/models.py`, and documented every route in `output/harness.md`. The server starts with the exact command given and the routes were tested.

### Follow-up prompt(s)

_None yet._

**What was lacking in the first prompt:** _To be filled in once a follow-up is needed._

---

## Problem 8: Agent dashboard

### Prompt 1

> Problem 8: Agent dashboard
>
> Build the frontend dashboard in frontend/ with React + Vite + TypeScript, which should call the routes from Problem 7. The board should at least (1) List all 3 tickets, (2) Let you pick one ticket and begin the agent team on it, (3) Show each agent and a record of what they are doing and saying while the ticket runs, (4) Mark a ticket as resolved when the run finishes, (5) Display a concise summary of what each agent did on that ticket, (6) Let a human approve a purchase or payment when necessary, (7) Display the checking balance (which should drop after a payment is approved).
>
> Make sure that the dashboard is styled nicely, with a frosted-glass bubbly appearance that is navy and white, modeled loosely off of the colors of the Yale Campus Customs website (https://yalebulldogblue.com/), that is friendly and inviting, yet professional. It should also have really cool animations and motion (be creative!).
>
> The frontend should talk to the backend at http://localhost:8000. From the backend, allow the Vite page origin (usually http://localhost:5173), such that the browser is allowed to call the routes. Start the board with the following command, which opens the Rect desk in the browser such that a person can pick tickets and watch agents: npm run dev
>
> Then, write the document output/design.md to explain what you chose the dashboard to look like (the layout, how the agents read differently, how resolved tickets and cash appears) and WHY. Include explanations for the creative choices that make the dashboard feel special and something people would enjoy to use.

**Outcome:** Claude built the React + Vite + TypeScript dashboard in `frontend/`, added a resolve route and run-finish closing to the backend, and wrote `output/design.md`. It was tested in the browser against the real backend routes with scripted (no-token) agents.

### Follow-up prompt(s)

_None yet._

**What was lacking in the first prompt:** _To be filled in once a follow-up is needed._

---

## Problem 9: Resolve the tickets

### Prompt 1

> Problem 9: Resolve the tickets
>
> Before you test the agents on a full run over the 3 tickets, please reset the working database data/campus_customs_new.db such that it starts off clean to how it was at the beginning. Please note the starting checking balance, and then go ahead and run all 3 tickets that are on the board until they are all resolved (101, 102, and 103). Then, open output/desk_tickets.html (from Problem 6). Fill the 'Actual' section on EACH ticket tab from this run with the contents of (1) what agents worked, (2) what they delegated, and (3) what tools they used. Don't change the Expected section, so that you can compare the Actual and Expected.
>
> Then, in the output/desk_tickets.html file, on the 'Cash' tab, itemize the money, including (1) Starting checking balance after the reset, (2) For EVERY ticket, how cash changed when that ticket was resolved and why, including details of the pay / purchase and dollar amount, and (3) Ending checking balance, which must match cash_accounts in the working database.
>
> Audit yourself and make sure that the cash math is correct and everything adds up.
>
> Additionally, please write in output/resolved_tickets.json for each ticket, the id, final status, short outcome, what each agent contributed in the task, and any human approvals that were required.
>
> Also, please create output/resolved_board.html to be a page you can double-click with a screenshot of the React board for EACH of the resolved tickets (101, 102, and 103).
>
> Please also make sure to append the real runs to output/audit_trail.json, and add to output/harness.md such that it covers all the tables, MCP tools, all 5 agents, API routes, the dashboard, and all the safety rules (make sure these are comprehensive).

**Outcome:** Claude reset the working database (starting balance $3,400.00), ran the three tickets with the real agents through the dashboard, had the payments and decision approved from the dashboard, filled the Actual and Cash tabs, wrote `output/resolved_tickets.json` and `output/resolved_board.html` (with screenshots in `output/screenshots/`), appended the runs to `output/audit_trail.json`, and expanded `output/harness.md`. Ending balance $160.00.

### Follow-up prompt(s)

_None yet._

**What was lacking in the first prompt:** _To be filled in once a follow-up is needed._

---

## Problem 10: Reflection

### Prompt 1

> Problem 10: Reflection
>
> Now let's fill the Reflection tab in output/desk_tickets.html. For each of these questions, please be extremely detailed and thorough. Answer in my voice in a sophisticated yet friendly manner.
> (1) For each ticket, How would you evaluate the performance of the agents and why?
> (2) For each ticket, how did Actual compare to the Expected plan?
> (3) What could have been more simple as just one agent with tools, and why would you say this?
> (4) Describe 3 NEW problems that the Campus Customs business may face that this system of agents could solve with the existing tools (and how would they solve these problems?)
> (5) Describe 3 NEW problems that the Campus Customs business may face that this system of agents would NOT be able to solve with the existing tools, and for each new problem, think of and explain the new tools and/or agents that would need to be built to solve these problems.
>
> Tie every single answer of these question to THIS app and these 3 specific tickets that we ran. Use the ticket tabs and cash tabs as evidence for answering these questions. I am graded on this specificity, so I need Campus Customs details in each answer.

**Outcome:** Claude filled the Reflection tab of `output/desk_tickets.html` in the first person, using the audit trail (requests, tokens, tool calls, timings), the Ticket tabs (Expected vs Actual) and the Cash tab as evidence for all five questions.

### Follow-up prompt(s)

_None yet._

**What was lacking in the first prompt:** _To be filled in once a follow-up is needed._

---

## Follow-up messages logged after the problems above

These are things typed to Claude after a problem's main prompt, listed here so the log covers everything typed.

### Problem 6 (title correction)

> Just a quick correction in the prompts file. Problem six should be titled Problem 6: Plan the three tickets

**Outcome:** the Problem 6 heading was changed to "Problem 6: Plan the three tickets". **What was lacking in the first prompt:** the title was written with the numeral "3", and the spelled-out "three" the log should use was not specified.

### Problem 10 (status question)

> Why does status write that three agents wrote the status field on 103?

**Outcome:** the audit trail showed only two agents (Accounting, then Customer Service) wrote the status; the Boss only added a note. The two sentences in the Reflection tab were corrected. **What was lacking in the first prompt:** it asked for specificity but not for every count to be checked against the audit trail, so an unverified count slipped in.

### Final audit

> Do a final audit of your work. Does everything make sense? Do all the numbers check out? I told you not to invent any numbers, so please make sure this is true as well

**Outcome:** every dollar figure in the deliverables was checked against the database or recomputed; unsupported numbers were removed or labelled (a token-saving estimate was removed, hypothetical inputs were labelled, a note was added to `output/mcp_smoke.json`, and `output/harness.md` now lists the numbers that are design choices rather than shop data).

---

## Problem 11: Submit to GitHub

### Prompt 1

> Problem 11: Submit to GitHub
>
> Ok, now let's push this code to a public GitHub repository such that graders of this assignment will be able to clone it. Put the Github repo URL in output/github_url.txt. Note: Please do NOT push the real .env file to the GitHub repo, but please DO include both database files (both the original and working copy) under data/ . The expected file layout is attached, so please make sure that the GitHub repo files follow this format. The README.md file should explain to copy the original database to the working copy when you need a clean run, start the MCP server, start the FastAPI backend, start the React dashboard, reset the database before a full 3 ticket run.
>
> (Attached: a screenshot of the expected file layout for `hw5/`.)

**Outcome:** Claude scanned for secrets, added `README.md`, `requirements.txt`, `.env.example` and `.gitignore`, created the public repo https://github.com/beatricek222/campus-customs-hw5, wrote the URL to `output/github_url.txt`, and pushed both databases but not the real `.env`.

### Follow-up prompt(s)

_None yet._

**What was lacking in the first prompt:** _To be filled in once a follow-up is needed._
