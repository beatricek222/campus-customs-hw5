# Campus Customs Desk: dashboard design

The dashboard (`frontend/`, React + Vite + TypeScript, talking to the FastAPI backend at http://localhost:8000) is a single "desk" where a person picks a ticket, watches the five agents work on it, and then makes the one decision that is theirs: approving money. Start it with `npm run dev` from `frontend/`.

## The look, and why

**Navy and white, frosted glass, soft round shapes.** The page sits on a deep Yale-blue gradient (`#00356B` family, going to near-black navy at the edges). Every panel is translucent frosted glass (blur, a faint white border, a bright top edge) so it feels like looking through a window at the shop. The only solid white is where something *matters*: the balance purse, the agents' speech bubbles and primary buttons.
*Why:* Yale's identity is blue and white, and a dark navy field makes the white content read clearly and look calm. Frosted glass says "modern and friendly" while staying professional, and rounding everything (pill top bar, 26px cards, circular avatars) makes a screen full of money and agents feel welcoming instead of like a spreadsheet.

**Serif headings, sans body.** Headings use a classic serif (Iowan Old Style / Palatino / Georgia) and everything else is the system sans-serif.
*Why:* the serif nods to Yale and a university shop; the sans keeps long agent text easy to scan. No web fonts, so it loads instantly and works offline.

**Floating bubbles in the background.** Large translucent spheres drift slowly behind the glass.
*Why:* they give the frosted glass something to blur (so it actually looks like glass), add depth, and give the page a quiet "alive" feeling even when nothing is running.

## Layout

1. **Top bar (a glass pill):** the crest and name on the left, the **checking balance** in the centre, a **Reset desk** button on the right. The balance is always visible because every ticket is really a question about the same cash.
2. **Left column: the three tickets** as cards (type icon, subject, requester, SKU/amount chips, status badge, a **Run team** button). A counter shows how many are resolved.
3. **Right side, for the selected ticket:**
   - a header with the ticket and its status;
   - **The team** (the agent ring) and, only when needed, the **approval card**;
   - the **Live conversation** feed;
   - underneath, **What each agent did**: one summary card per agent.

*Why this order:* it follows how a person thinks. Pick work (left), see who is doing it and what they say (middle/right), then read the conclusion (bottom). The approval card sits directly under the team, so the moment something needs a human it is the most visible thing on screen. On narrow screens everything stacks in the same order.

## How the agents read differently

Every agent has its own **icon, accent colour and place on the ring**, used consistently in the ring, the feed and the summaries:

| Agent | Icon | Accent | Feel |
|---|---|---|---|
| Boss | crown | gold | the leader; also the one that writes the final answer |
| Inventory | box | sky blue | stock and prices |
| Accounting | coin | mint | money |
| Facilities | building | lilac | leases and rent |
| Customer Service | speech bubble | rose | the friendly voice |

*Why:* a reader should be able to tell who is speaking without reading the name. The accents are small touches on a navy-white base, so the page still reads as navy and white.

The things agents do also look different from each other:
- **Said / thought:** a white speech bubble with the agent's name.
- **Tool use:** a small dark pill showing the tool name and arguments, with a spinner that turns into a green tick when the result returns (click it to see the raw result). These look like *actions*, not talk.
- **Delegation:** a tinted card that blends the two agents' colours ("Boss asks Inventory"), with the task, and the answer appearing inside it as "Inventory reports: ...". Delegation is the heart of the system, so it gets its own shape.
- **Final answer:** a white bubble with a coloured border.
- **Problems:** a soft red bubble.

## Making the agents feel alive

- **The team ring.** The five agents sit on a pentagon with a dotted line between every pair, which shows the **full connectivity** of the team. When an agent delegates, a glowing dot flies along the line from caller to callee, the line lights up, and a second dot flies back when the answer returns. You *see* the Boss pass the ticket to Facilities and Facilities answer.
- **Live status under each agent:** "Reading the request", "Using get_lease_due", "Asking Accounting", "Finished". An active agent scales up, glows in its own colour, sends out ripples and shows bouncing "typing" dots. A finished agent gets a green tick.
- **Agents that were not needed fade back and say "Not needed here".** This makes the *selectivity* of the Boss visible: the board shows that not every specialist was sent on every ticket.
- **The feed** pops in message by message with a springy bounce and auto-scrolls, so a run feels like watching a chat unfold. A red LIVE chip blinks while a run is in progress.

## Resolved tickets

- When a run ends and nothing is waiting on a person, the ticket is marked **Resolved**. When a person approves a payment or accepts a recommendation, it is marked Resolved too.
- The badge turns mint with a checkmark that **draws itself**, the card takes a green tint, the header gets a large check that draws a circle then a tick, and a **burst of navy, white, sky and gold bubbles** (confetti) fires. The Run button turns into "Done".
- The "x/3 resolved" counter ticks up.

*Why:* finishing a ticket is the payoff for the person using the board, so it should feel good. Green is used only for "done", so it never competes with the navy/white identity.

A ticket waiting on a person gets a gold "Needs your approval" badge that gently pulses, so the next action is impossible to miss.

## Cash and approvals

- **The balance is a white "coin purse"** in the middle of the top bar, the brightest object on the page, with a slow shine sweeping across it. The number **counts smoothly** to its new value and a **−$2,400.00 chip floats up** when a payment lands, so a payment is a visible, satisfying event, not a silent refresh. This is how you know the approval really changed the cash.
- **The approval card** has a gold glow and a waving hand. It states plainly what is being paid (amount, payee, due date) and says "The agents only prepared this. Nothing moves until you approve." It asks for **your name**, then needs **two clicks** ("Approve $2,400.00", then "Yes, confirm") that repeat the amount and payee. Money is the one place a deliberate extra step is worth it.
- For a ticket with no payment (the hoodie discount) the card shows the team's recommendation and an "Accept recommendation" button; a discount is a human decision, not a payment.
- Agents cannot pay: the backend only lets the approve route change cash.

## Delight, but with restraint

- Ticket cards **tilt in 3-D** toward the pointer with a soft highlight that follows it, and a running ticket gets a **spinning light border**.
- Cards **pop in** with a staggered spring on load, and the crest gently bobs.
- A green dot in the header **pings** while the backend is connected; if it cannot be reached the page says exactly which command to run.
- Everything respects the system "reduce motion" setting, and all controls work from the keyboard.

## What is deliberately not there

No charts, no tables of rows, no jargon in the main view (tool names appear only as small pills). The goal is that someone who has never seen the system can pick a ticket, understand what the team did, and make the one decision that is theirs.
