# PRISM - Product Requirements Document (PRD)

> Portfolio-aware investment research copilot for India buy-side relationship managers.
> This is Part A (Product) of the original scoping document. The companion [Low-Level Design](LLD.md) covers the technical design.

---

## Executive summary

Investment teams spend disproportionate effort reading and re-summarising the same universe of market content, then manually translating it into portfolio implications. The reading is not the bottleneck; the **translation from event to "what it means for our book"** is. Existing summarisation tools stop at the summary. This product goes one step further and links every insight to the fund's actual holdings, sector exposures, and risk positions.

The wedge, and the moat, is **portfolio-aware grounding**. A generic tool tells you a company was downgraded. This tells you the downgrade touches 4.2% of Fund A's NAV across three held names and lifts your semiconductor factor tilt. Because it operates in a regulated context, every claim is citation-grounded and traceable to a source, and the system stays firmly in decision-support territory rather than issuing advice or executing trades.

Everyone can summarise. Almost no one connects the summary to your book with a citation you can defend to compliance. That connection is the product.

## Problem & context

Buy-side research analysts and portfolio managers face a continuous, high-volume inbound stream: sell-side broker notes, earnings-call transcripts, regulatory filings, real-time news, market commentary, and their own firm's internal research. The manual workflow is expensive on three fronts:

- **Volume triage.** Deciding what, out of hundreds of daily items, is even relevant to the positions they hold.
- **Synthesis.** Compressing long documents into the few sentences that matter, repeatedly, across overlapping sources.
- **Translation to the book.** Connecting an external event to specific holdings, sector exposures, and risk positions. This is the step that carries the real cognitive load and is the least supported by existing tooling.

The consequence is slower decision support, uneven coverage (well-followed names get attention; the long tail is neglected), and senior analyst time spent on low-leverage reading rather than judgement. The CIO office, meanwhile, lacks a consolidated, timely view of how unfolding events map onto the firm's aggregate exposures.

#### Why now

Long-context LLMs make document synthesis reliable and cheap; grounded retrieval makes citations enforceable; and firms are actively standing up research GCCs and AI functions, creating both the demand and the delivery capacity for exactly this class of tool.

## Goals & non-goals

#### Goals

- Cut time-to-insight per material event by a target of 60% or more.
- Link surfaced insights to specific held positions with high precision.
- Raise coverage of the held universe, especially long-tail names.
- Give the CIO office a firm-wide event-to-exposure oversight view.
- Make every insight defensible: cited, traceable, reproducible.

#### Non-goals (for v1)

- No trade execution, order routing, or portfolio rebalancing.
- No personalised investment advice to end investors.
- No price prediction, alpha signals, or quant factor models.
- No replacement of the OMS, EMS, or system of record.
- No fully autonomous action; a human stays in the loop.

PRISM is a research productivity and oversight tool, not an advisory or trading system. This boundary is a product decision, not just a compliance one, and it keeps the surface area shippable.

## Personas & jobs to be done

The user and the buyer are different people. Design must satisfy both or the product dies in the gap between them.

### Research analyst

*"When a name I cover reports or moves, help me understand the read-through to our positions fast, with sources I can cite in my note."*

#### Cares about

- Speed and coverage
- Trustworthy citations
- Not missing material events

### Portfolio manager

*"Tell me which of my holdings are affected by what's happening today, and how much of my book is exposed."*

#### Cares about

- Book-level relevance
- Risk and exposure context
- A fast morning digest

### CIO office

*"Give me firm-wide oversight of how events map to our aggregate exposures, and evidence the desks are covered."*

#### Cares about

- Oversight and consistency
- Auditability and control
- Demonstrable productivity

### Research GCC lead

*"Let my offshore team support many global desks at once without re-learning each book's context by hand."*

#### Cares about

- Multi-desk, multi-portfolio
- Entitlements and access
- Repeatable workflows

## Success metrics

| Tier | Metric | Definition | Target (pilot) |
| --- | --- | --- | --- |
| North star | Time-to-insight | Median minutes from a material event to a cited, book-linked summary in front of the analyst | < 5 min |
| Value | Held-universe coverage | % of held names with at least one fresh, linked insight per week | > 90% |
| Quality | Linkage precision | % of holding links judged correct on audit | > 92% |
| Trust | Citation accuracy | % of claims whose cited source actually supports them | > 98% |
| Adoption | Weekly active analysts | Distinct users running ≥ 3 sessions/week on the pilot desk | > 70% |
| Outcome | Self-reported time saved | Hours/week per analyst, survey-based | ≥ 5 hrs |

Raw summary quality is table stakes and hard to move a buyer with. Time-to-insight and coverage are what leadership feels. Citation accuracy is the metric that, if it slips, ends the pilot regardless of the others.

## Feature scope (MoSCoW)

| Priority | Capability | Notes |
| --- | --- | --- |
| Must | Multi-source ingestion & normalisation | Transcripts, filings, news, internal notes into one schema |
| Must | Grounded summarisation | Per-document and per-event, every claim cited |
| Must | Holdings linkage | Insight to specific positions. The wedge. |
| Must | Sector / exposure roll-up | "3 held names touched, 4.2% of NAV" |
| Must | Grounded analyst Q&A | Chat over the corpus with citations and filters |
| Should | Personalised daily digest | Per-PM, scoped to their book |
| Should | Material-event alerting | Push when news hits a held name above a threshold |
| Should | Risk-position flagging | Concentration and factor-tilt shifts from an event |
| Could | Thematic clustering | Auto-surface emerging cross-source themes |
| Could | CIO oversight dashboard | Firm-wide event-to-exposure heatmap |
| Won't (v1) | Trade execution / rebalancing | Explicit non-goal |
| Won't (v1) | Alpha / price prediction | Out of scope and out of positioning |

## Key user journeys

### J1. Morning book scan (PM)

PM opens PRISM. Dashboard shows overnight material events touching held names, ranked by NAV impact. Each row expands to a cited summary and the affected positions. Two minutes replaces a half-hour scan.

### J2. Earnings read-through (analyst)

A covered name reports. PRISM ingests the transcript, produces a cited summary, and highlights which of the firm's holdings share supply-chain, sector, or factor exposure. Analyst asks follow-ups in chat, then lifts cited lines straight into their internal note.

### J3. Ad-hoc question (analyst)

"What did brokers say about our semiconductor holdings this quarter, and what's the risk read-through?" PRISM retrieves across the corpus, answers with inline citations, and lists the positions in scope, filterable by fund, sector, and date.

### J4. Oversight review (CIO office)

CIO office views the firm-wide heatmap of events against aggregate exposures, confirms coverage of the held universe, and drills into any desk. Audit log records who saw what.

## Functional requirements

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-01 | Ingest documents from transcripts, filings, news feeds, and uploaded internal notes; deduplicate near-identical items. | Must |
| FR-02 | Resolve company and instrument mentions in text to the firm's holdings, including aliases, tickers, ADRs, and subsidiary-to-parent. | Must |
| FR-03 | Generate document- and event-level summaries where every claim carries an inline citation to a source span. | Must |
| FR-04 | For any event, compute affected holdings, % of NAV exposed, and sector breakdown. | Must |
| FR-05 | Answer natural-language questions over the corpus with citations; support filters by fund, sector, entity, and date. | Must |
| FR-06 | Enforce per-user, per-desk entitlements on both documents and portfolios. | Must |
| FR-07 | Produce a personalised digest per PM on a schedule, scoped to their holdings. | Should |
| FR-08 | Alert users when a material event hits a held name above a configurable threshold. | Should |
| FR-09 | Flag concentration and factor-tilt changes implied by an event. | Should |
| FR-10 | Maintain an immutable audit log of queries, sources shown, and outputs. | Must |

## Non-functional requirements

| Category | Requirement |
| --- | --- |
| Latency | Interactive Q&A first token < 3s; full grounded answer < 12s. New-document ingest-to-searchable < 5 min. |
| Accuracy | Linkage precision > 92%; citation faithfulness > 98% on the eval set (see §22). |
| Security | Encryption in transit and at rest; row-level entitlement enforcement; no training on client data; tenant isolation. |
| Auditability | Every surfaced claim reproducible to its source span; full query and access logging retained per policy. |
| Reliability | Graceful degradation: if linkage confidence is low, show the summary and flag the uncertainty rather than guessing. |
| Scalability | Multi-tenant, multi-desk, multi-portfolio from day one; ingest volume scalable independent of query load. |
| Privacy | Internal research never leaves the tenant boundary; configurable data residency. |

## Data sources & licensing

Data licensing, not the model, is the true commercial critical path. The MVP is deliberately built on defensible public sources; licensed sources are a parallel workstream, not a blocker.

| Source | MVP status | Notes |
| --- | --- | --- |
| Earnings-call transcripts | Public subset | Publicly posted transcripts for the pilot; licensed feed for production |
| Regulatory filings | Public | SEC EDGAR / exchange filings, freely usable |
| News & market commentary | Licensed API | News API with clear redistribution terms |
| Internal research notes | Tenant-supplied | Uploaded by the firm; never leaves the tenant |
| Sell-side broker reports | Deferred | Paywalled/licensed. Production only, with entitlement checks. Do not use in MVP. |
| Holdings & exposures | Tenant-supplied | From the firm's system of record; the linkage target |

## Compliance & guardrails

- **Human in the loop, always.** Output is decision-support; no automated action is taken on the book.
- **No advice generation.** The system does not issue buy/sell recommendations or personalised investment advice.
- **Grounding is mandatory.** Claims without a supporting source span are suppressed, not shown with a guess.
- **Entitlement-aware.** Users only see documents and portfolios they are cleared for; licensed content respects its terms.
- **Full audit trail.** Every query, source shown, and output is logged and reproducible.
- **MNPI hygiene.** Clear handling boundary for any material non-public information; internal notes stay inside the tenant.

## Risk register

| ID | Risk | Sev. | Mitigation |
| --- | --- | --- | --- |
| R-01 | Entity linking too inaccurate to trust; wrong holdings surfaced | High | Front-load a Phase-0 spike; hybrid symbolic + LLM resolver; show confidence; fail closed |
| R-02 | Hallucinated or unsupported implications in a regulated setting | High | Mandatory citation grounding; claim-level verification; suppress ungrounded output |
| R-03 | Broker-report licensing blocks production value | High | MVP on public sources; licensing as a parallel commercial workstream |
| R-04 | Buyer sees it as "just another summariser" | Med | Lead every demo with the holdings-linkage wow-moment, not the summary |
| R-05 | Adoption stalls; analysts distrust and revert | Med | Citations on every claim; pilot with a friendly desk; measure time saved |
| R-06 | Data residency / security objections from IT | Med | Tenant isolation, no training on client data, configurable residency |
| R-07 | Cost per query scales badly with corpus size | Low | Tiered models: cheap for bulk summarisation, top-tier for reasoning; caching |
