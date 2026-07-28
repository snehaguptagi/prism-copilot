# PRISM - Product Requirements Document (PRD)

> Portfolio-aware investment research copilot for India buy-side relationship managers (RMs).
> This document describes the product as actually built. The companion
> [Low-Level Design](LLD.md) covers the technical design, data model, pipeline, and the
> external APIs the system uses.

---

## 1. Overall picture

PRISM is a decision-support tool for a relationship manager who runs a book of private-wealth
clients in the Indian market. It answers one question that generic news and research tools do
not: **"today's market moved, so which of MY clients does it touch, by how much, and what do I
tell them?"**

A generic tool tells you the rupee fell or the RBI held rates. PRISM tells you that the move is a
headwind for 95% of Suresh Nair's bond ladder, a tailwind for Vikram Oberoi's concentrated bank
book, and hands you a one-line, persona-aware talking point for each. Every surfaced number is
computed deterministically from real holdings, and every market claim is grounded in a cited
source.

The shipped product is a single-tenant demo over a synthetic but realistic India-only dataset:
one logged-in RM (Sneha Gupta) managing **16 client portfolios** worth roughly **Rs 177 crore**,
spanning a Rs 38 lakh young trader to a Rs 46 crore business promoter. It is built entirely around
Indian instruments (NSE/BSE equities, G-secs, corporate bonds, gold ETFs and SGBs, REITs) and
Indian macro drivers (RBI policy, the rupee, oil, gold). There is no US-centric content and no
crypto anywhere.

### What the RM gets

| Surface | What it answers |
|---|---|
| **Overview** | The whole book at a glance: AUM, fee revenue, risk spread, asset and sector allocation, top holdings, book return vs the Nifty, and what needs attention today. |
| **Clients** | A roster of 16 distinct personas, each with a full profile: behavioral psychographics, relationship insights, holdings, performance vs the Nifty, a suitability check, and a communication log with the next action due. |
| **Analysis** | Pick a client's book, run live grounded research on its dominant exposure, and get exposure vs a normal book plus tailored talking points. |
| **News Feed** | Categorized live market news reduced to a one-line TL;DR, clean key-point bullets, and, for each affected client, a specific "what to tell them" talking point. |
| **Products** | The investable universe the desk can offer, grouped by asset class. |

## 2. Problem and context

An RM's day is a continuous inbound stream: market moves, RBI decisions, currency swings,
earnings, sector news. The manual workflow is expensive on three fronts:

- **Triage.** Deciding which of dozens of daily developments is even relevant to the positions
  their clients actually hold.
- **Translation to the book.** Connecting an external event to specific holdings and exposures.
  This is the step that carries the real cognitive load and is the least supported by existing
  tooling.
- **Client communication.** Turning "what happened" into a short, correct, persona-appropriate
  message for each affected client, fast enough to be useful the same day.

The consequence is slower client response, uneven coverage (big holdings get attention, the long
tail is neglected), and senior time spent reading rather than advising.

#### Why this is tractable now

Long-context LLMs make document synthesis reliable and cheap; a hosted, cited web-search tool
makes grounding enforceable without running a scraper; and deterministic arithmetic over holdings
makes every impact number defensible to compliance. PRISM combines the three.

## 3. Goals and non-goals

#### Goals

- Cut the time from "a thing happened in the market" to "a cited, book-specific read" to under a
  few minutes.
- Link every surfaced insight to specific held positions with high precision.
- Give the RM a firm-wide, one-screen view of the book (AUM, risk, allocation, performance).
- Produce short, persona-aware client talking points on demand.
- Make every insight defensible: cited, traceable, and reproducible.

#### Non-goals

- **No advice.** PRISM never says what to buy, sell, or hold, and never executes trades. It is
  observational decision support only.
- **No real trading or custody integration.** The dataset is synthetic.
- **Not multi-market.** India only. No US equities, no crypto or digital assets.
- **Not multi-tenant in the demo.** One RM, no login, single book.

## 4. Personas

#### The user: the relationship manager

Sneha Gupta manages a book of 16 private-wealth clients. She is time-poor, needs to respond to
clients the same day a story breaks, and has to keep every claim defensible. She is the only
logged-in user; there is no authentication in the demo.

#### The clients (the 16 personas the book is built from)

The clients are deliberately diverse in wealth, sophistication, risk appetite, and communication
style, because the whole point is that the same news lands differently on each. A sample:

- **Meena Iyer**, 68, retired schoolteacher, capital-preservation book (Rs 1.35 Cr), loss-averse,
  wants reassurance not returns.
- **Rohan Mehta**, 29, software engineer, all-IT conviction book (Rs 1.55 Cr), reads every
  earnings call, wants a research partner who keeps up.
- **Arjun Verma**, 22, full-time trader, aggressive small and midcap book (Rs 38 lakh), checks
  prices several times a day.
- **Vikram Oberoi**, 52, ex-banker angel investor, concentrated banks book (Rs 13.5 Cr), expert,
  pushes back if the book gets diluted.
- **Rajiv Malhotra**, 59, business promoter post partial exit, diversified equity (Rs 46 Cr).
- **Suhas Kamath**, 44, tech founder post exit, aggressive growth (Rs 30 Cr).
- **Anjali Bhandari**, 46, second-generation family office, multi-asset (Rs 38 Cr).
- **Dr. Venkat and Latha Reddy**, 61, physician couple, capital-protective blue-chip (Rs 22 Cr).

The full roster of 16 spans retirees, salaried professionals, an NRI couple, a homemaker with
family gold wealth, a passive index investor, a small business owner, and the UHNI anchors above.

## 5. Feature scope

All five surfaces below are built and working.

#### Overview (firm-wide dashboard)

Total AUM, client count, annual fee revenue, blended fee rate, distinct securities, book return
vs the Nifty 50 with best and worst performer, "what needs attention" action items sorted by due
date, asset-class allocation, AUM by risk tier, sector exposure, largest positions, and largest
clients. Every figure is computed from current holdings, nothing estimated.

#### Clients (roster + client detail)

A searchable, risk-filterable roster. Each client detail page has four tabs: **Profile** (persona,
behavioral psychographics, goals, relationship insights, manager note), **Portfolio** (performance
vs Nifty, suitability check, metrics, sector allocation, factor sensitivity, largest position),
**Holdings** (every position with weight and market value), and **Communication** (the PM-to-client
interaction log plus the next action due).

#### Analysis (portfolio-first research flow)

Pick a client card, and PRISM runs grounded research on that book's dominant exposure, then shows
a verdict banner, exposure gauges, a tailwind/headwind bar, market-insight bullets, tailored
talking points, and cited sources.

#### News Feed (daily briefing)

Seven India-relevant categories (India Markets, Global cues for India, Commodities and Energy,
Currency and Rates, Corporate Earnings, Policy and Regulation, India Startups). Each renders a
one-line TL;DR, key-stat callouts, scannable key-development bullets, and a "what to tell your
clients" section: the eight most-affected clients, each with a named-factor exposure line and a
specific talking point. Cached per category so it does not reload on its own, with a manual Reload
button.

#### Products (investable universe)

The full security master the desk can offer, grouped by asset class, with usage counts.

## 6. Functional requirements

- **FR1.** Research calls must be grounded: every market claim carries a citation to a source, or
  it is suppressed.
- **FR2.** All impact numbers (NAV touched, tailwind/headwind, exposure vs a normal book,
  performance, suitability) are computed deterministically from holdings. The LLM only phrases
  them; it never computes or invents numbers.
- **FR3.** All content is India-only. Crypto and digital assets are never mentioned.
- **FR4.** Talking points are one sentence, persona-aware, and lead with the concrete fact.
- **FR5.** The News Feed is cached (in-process on the server and on the device) and refreshes only
  on explicit Reload.
- **FR6.** No buy/sell/hold guidance is generated at any stage.

## 7. Non-functional requirements

- **Correctness and defensibility.** The deterministic core is fully unit-tested (88 tests). Any
  number shown can be traced to holdings and reproduced.
- **Latency.** Cached surfaces open instantly. Live research is bounded (capped web searches,
  tiered models) to keep a research call to a small number of seconds.
- **House style.** Concise, data-first output. No em dashes. Lead with the number.
- **Privacy.** No real client data; the dataset is synthetic.

## 8. Compliance and guardrails

- Decision-support only: observational output, never advice, never execution.
- Every market claim is citation-grounded and traceable.
- A suitability check flags any book that has drifted more aggressive or more conservative than
  the client's stated mandate, before compliance has to.
- The model is explicitly instructed never to use words like "recommend", "should invest", or
  "opportunity".

## 9. Success criteria

| Dimension | What good looks like |
|---|---|
| Grounding | Every market claim has a working citation. |
| Linkage | Impact maps to the right holdings; percentages are correct and bounded. |
| Usefulness | Talking points read like something the RM would actually say to that client. |
| Trust | Any figure can be reproduced from the dataset. |
| Coverage | The whole book is visible, not just the big names. |

## 10. Data note

All client, portfolio, and communication data is synthetic, built to demonstrate the workflow
realistically. It does not represent real people or real accounts. Performance figures are
illustrative of each strategy's character, not derived from live price history.
