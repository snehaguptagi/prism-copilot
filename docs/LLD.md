# PRISM - Low-Level Design (LLD)

> Technical design of PRISM as built: architecture, the external APIs used, data model, the
> research-to-insight pipeline, the deterministic engines, the HTTP API surface, tech stack, and
> how to run it. See the [Product Requirements Document](PRD.md) for product scope.

---

## 1. Overall picture

PRISM is a two-process web app plus a synthetic data generator:

```
                         build_dataset.py            RM edits at runtime
                    (synthetic India dataset gen)   (add client, edit holdings,
                                 |                   fill in profile)
                                 v                          |
                        backend/prism_data.json             v
                          (seed, read-only)     backend/prism_overlay.json
                                 |    \                    /
                                 |     merged by load_data()
                                 |          on every read
                                 |
  ┌───────────────┐   HTTP   ┌───────────────────────────┐   HTTPS   ┌────────────────────────┐
  │  Next.js UI    │ ───────> │  FastAPI backend          │ ────────> │  Anthropic Claude API   │
  │  (browser)     │ <─────── │  api.py + insight_lens.py │ <──────── │  + hosted web_search    │
  └───────────────┘   JSON   └───────────────────────────┘   cited   └────────────────────────┘
       5 tabs                  deterministic engines +                 grounded research,
                               LLM narration                           returns citations
```

- **Frontend** (`frontend/`): a Next.js + TypeScript app with five routes (Overview, Clients,
  Analysis, News Feed, Products). It is a thin rendering layer; all numbers come from the backend.
- **Backend** (`backend/`): a FastAPI service. `api.py` exposes the HTTP surface and holds the
  deterministic roll-up engines; `insight_lens.py` is the research-and-narration pipeline that
  calls Claude.
- **Data**: `build_dataset.py` generates `prism_data.json`, a self-contained synthetic dataset of
  desks, portfolios, securities, holdings, risk, and a benchmark. It is treated as read-only at
  runtime. Anything the RM enters by hand goes into a separate `prism_overlay.json`, which
  `load_data()` merges over the seed on every request (section 4.1), so regenerating the demo
  dataset never destroys entered data and no restart is needed to see an edit.

The central design rule is a strict **division of labor**: every number is computed by
deterministic Python from holdings; the LLM only phrases those numbers and grounds market claims
in citations. The model never computes or invents a figure.

## 2. External APIs used

PRISM uses exactly one external API in the running system. The originally-scoped market-data
vendors were evaluated but not needed, because Claude's hosted web-search tool provides grounded,
already-cited retrieval in a single call.

### Anthropic Claude API (the only live dependency)

| Use | Model | How |
|---|---|---|
| Grounded market research | `claude-sonnet-5` | Messages API with the hosted **`web_search_20250305`** server tool (`max_uses = 4`). Claude runs the searches under Anthropic's terms and returns answer text plus structured citations. No scraper is run by PRISM. |
| News briefing and talking points | `claude-sonnet-5` | Messages API with a forced structured-output tool call (`record_briefing`, `record_talking_points`) so the response is validated JSON, not free text. |
| Factor classification | `claude-haiku-4-5-20251001` | Cheap, fast pass that reads a research narrative and tags macro factor signals (gold, oil, Indian rates, US rates, rupee) with a direction. |

- **Auth**: a single `ANTHROPIC_API_KEY` environment variable (loaded from `backend/.env` via
  `python-dotenv`). No other secret is required.
- **Grounding**: citations come straight out of Claude's `web_search_result_location` content
  blocks. A market claim with no supporting citation is dropped, never shown.
- **Cost and latency control**: web searches are capped (`MAX_SEARCHES = 4`), a cheaper model does
  the classification pass, and results are cached (see section 8).

### Free market-data APIs (considered, not used)

During scoping, three free-tier market-data APIs were candidates for the raw news/quote feed:

| API | Free tier | Why it was not used |
|---|---|---|
| **Finnhub** | Free API key, real-time quotes and company news | Would need separate entity extraction and citation handling; Claude's web_search returns cited prose directly. |
| **Marketaux** | Free tier, news with entity tagging | Overlaps with what the hosted web search already returns, with less flexible querying. |
| **NewsAPI** | Free developer tier, headline search | Headlines only, no grounding or citations; still needs an LLM pass to be useful. |

They remain the natural drop-in if PRISM ever needs deterministic, structured price/news feeds
(for example, real historical NAV to replace the illustrative performance figures). The pipeline
is deliberately structured so a market-data adapter could feed the same `link_citations_to_securities`
and roll-up stages.

## 3. Component design

| Component | File | Responsibility |
|---|---|---|
| HTTP API | `backend/api.py` | Routes, request validation, the deterministic roll-up helpers (sector breakdown, performance, suitability, overview aggregation, news-feed assembly), and in-process caching. |
| Research pipeline | `backend/insight_lens.py` | Everything that touches Claude: grounded search, citation extraction, entity linking, factor detection, and the structured narration calls. Also runs standalone as a CLI. |
| Dataset generator | `backend/build_dataset.py` | Builds the synthetic India dataset (securities master, 16 client portfolios plus a reference benchmark, psychographics, communications, performance) and writes `prism_data.json`. |
| Frontend | `frontend/src/` | Next.js App Router pages, a typed API client (`lib/api.ts`), shared types (`lib/types.ts`), and an adaptive currency formatter (`lib/format.ts`). |

## 4. Data model

`prism_data.json` has six top-level collections. The shapes below are the actual fields.

```
Desk       { desk_id, tenant_id, name }

Portfolio  { portfolio_id, desk_id, name, base_ccy, risk_driver, mandate,
             manager_name, manager_bio,
             client { name, age, occupation, persona, email, phone, city,
                      relationship_since, aum_fee_pct, risk_mandate,
                      psychographics{...}, relationship{...},
                      communications[...], next_action{...} },
             performance { ytd_pct, one_year_pct, three_year_cagr_pct,
                           since_inception_cagr_pct } }

Security   { security_id, primary_ticker, name, aliases[], isin,
             parent_id?, adr_of?, sector, industry, country,
             asset_class, instrument_type, factor_sensitivities{...},
             vol, beta, cap_tier, credit_quality }

Holding    { holding_id, portfolio_id, security_id, weight,
             market_value, as_of_date }

Risk       { <portfolio_id>: { risk_score, risk_tier, est_vol, asset_mix,
             largest_class, top1_pct, top1_name, eq_hhi, wtd_beta, ... } }

Benchmark  { name: "Nifty 50", ytd_pct, one_year_pct, three_year_cagr_pct }
```

- **Linkage target**: `Security` is the entity every citation is linked to, via
  `primary_ticker`, `name`, and `aliases`.
- **Factor sensitivities**: each security is hand-tagged with its sensitivity
  (`positive` / `negative` / `same_direction`) to each macro factor, a stand-in for a full
  factor-model matrix.
- **Weights** are stored normalized (they sum to 1.0 per portfolio); `market_value = nav * weight`.
- One portfolio (`pf_reference_balanced`) is a fixed 60/40 benchmark, not a client, used for the
  "you vs a normal book" comparison.

Current dataset: **69 securities, 16 client portfolios + 1 reference, 219 holdings**.

### 4.1 Runtime-edit overlay

The demo dataset is the starting point for an RM's own data, not a wall around it. Everything
entered at runtime is persisted to `backend/prism_overlay.json`, and `load_data()` returns
`apply_overlay(seed, overlay)` on every read.

```
Overlay { version,
          portfolios[]          # whole portfolios added at runtime (flagged custom: true)
          client_overrides{}    # portfolio_id -> partial client dict (persona, psychographics)
          holdings{}            # portfolio_id -> FULL replacement holdings list
          risk{}                # portfolio_id -> recomputed risk block
        }
```

Why a second file rather than writing back into `prism_data.json`:

- **`build_dataset.py` stays safe to run.** Regenerating the seed dataset used to silently delete
  every client the RM had added. Now the two never touch.
- **The demo stays reproducible.** Delete the overlay and the app is exactly the shipped 16
  personas. The file is gitignored, like `.env`.
- **Seed data cannot be corrupted.** No runtime path writes to `prism_data.json` at all, which is
  asserted directly in the tests (they compare the file byte for byte before and after).

Design notes:

- `holdings` is a **replacement**, not a merge, keyed per portfolio. Appending would leave removed
  positions in place and weights unable to sum to 1.
- `client_overrides` merges one level deep, and a `None` means "not supplied", so a partial profile
  edit never blanks fields it did not mention. This is why an override works on seeded clients too.
- Risk blocks in the overlay are always produced by `compute_portfolio_risk`, never hand-patched,
  so an edited book stays directly comparable to a seeded one.
- A malformed or hand-broken overlay is ignored rather than raised, so it cannot take the app down.
- The test suite moves any real overlay aside for the whole run (an autouse fixture), because the
  seed-data invariants it asserts, `client_count == 16` and similar, are about the seed data. Without
  that, adding one client through the UI would fail a dozen unrelated tests.

## 5. Research-to-insight pipeline

Both the Analysis flow and the News Feed run the same core pipeline in `insight_lens.py`. All
functions after the search are pure and deterministic.

1. **`run_search(sector)` / `run_news_feed(category)`** - one Claude call with the hosted
   `web_search_20250305` tool, India-focused prompt, capped at 4 searches. Returns cited prose.
2. **`extract_citations_and_narrative(response)`** - pulls the narrative text and structured
   citations out of Claude's content blocks (`server_tool_use` + `web_search_result_location`).
3. **`link_citations_to_securities(citations, securities)`** - entity linking: matches each
   citation to held securities by ticker / name / alias. This is the moat.
4. **`compute_portfolio_impact(data, linked)`** - deterministic roll-up: for each portfolio, the
   percentage of NAV touched by directly-cited holdings.
5. **`detect_factor_signals(narrative)`** - `claude-haiku` classifies which macro factors moved
   and in which direction. Signals are deduped to one per factor.
6. **`compute_factor_impact(data, signals)`** - deterministic: rolls up tailwind/headwind exposure
   per portfolio from the hand-tagged `factor_sensitivities`. Each holding counts once per factor,
   so a book's exposure to a single factor is bounded at 100% of NAV.
7. **`attach_reference_comparison(...)`** - expresses each book's exposure as a multiple of the
   60/40 reference book ("you vs a normal book").
8. **Narration** - `generate_talking_points(...)` and `generate_news_briefing(...)` make a single
   forced structured-output call each, turning the computed impact plus the cited narrative into a
   TL;DR, key points, and one persona-aware talking point per affected client. `max_tokens` is
   sized so the per-client array is never truncated.

Supporting engines: `detect_cross_desk_contradictions` (flags two books with opposing exposure to
the same factor) and `compute_scenario_impact` (mild/moderate/severe stress bands).

## 6. Product recommendation: rules and knowledge graph

PRISM recommends products to cross-sell in two layers, the second optional and additive to
the first.

**Layer 1: the rule-based recommender (`api.suggest_products`, always on).** Deterministic
Python. `_preference_profile` turns a client's stated goal, time horizon, loss aversion, and
life stage into a per-asset-class affinity score via keyword rules (e.g. "income" or
"withdraw" in the goal bumps Fixed Income; "inflation" or "gold" bumps Commodity). Candidates
are securities the client does not already hold, filtered to their mandate's risk-band
ceiling, ranked by affinity with a gap bonus toward asset classes the book lacks, capped at
two picks per asset class for variety. Every seeded client is guaranteed at least one
preference-matched suggestion (enforced by a test). This layer has no external dependency and
is what ships by default.

Because the affinity scores come entirely from stated preferences, **a client with no
psychographics scores every asset class at 0.0**. Suggestions still appear, ranked by mandate fit
and allocation gap, but none can honestly say "Matches their ...". That is the reason
`POST /clients` accepts a profile and `PUT /clients/{id}/profile` exists: without one, a
hand-added client is a second-class citizen on the Product Fit tab. Both the degraded fallback and
the recovery are pinned by tests, and the four fields that matter are surfaced to the UI as
`scoring_fields` rather than being tribal knowledge. The dropdown vocabulary in `PROFILE_OPTIONS`
is deliberately worded to contain the keywords the matcher looks for, and a test asserts every
option either moves a score or is on an explicit "deliberately neutral" list, so rewording an
option cannot silently turn it into a no-op.

**Layer 2: the Neo4j knowledge graph (`graph.py`, optional).** The same idea, but reasoned
over a graph instead of in-process Python, which is a more natural fit for "what do clients
like this one hold" (collaborative filtering) and multi-hop queries. The graph is populated by
`build_graph.py` from `prism_data.json`:

```
(:Client {portfolio_id, risk_tier, max_band, life_stage, time_horizon, loss_aversion, ...})
(:Product {security_id, name, asset_class, sector, band, ...})
(:AssetClass {name})   (:Sector {name})

(:Client)-[:HOLDS {weight}]->(:Product)
(:Client)-[:PREFERS {score}]->(:AssetClass)   # same affinity scores as layer 1, as edges
(:Product)-[:IN_CLASS]->(:AssetClass)
(:Product)-[:IN_SECTOR]->(:Sector)
```

The recommendation query walks a client to the asset classes they `PREFERS`, to products
there they do not `HOLD` and that fit their `max_band`, then ranks by how many *other* clients
with the same `life_stage` or `risk_tier` hold each product (`peers` count), the
collaborative-filtering signal a flat rule table cannot express. `graph.py` exposes
`graph_enabled()`, `ping()`, and `recommend_products(portfolio_id)`.

**Fully optional, fails closed.** `graph.graph_enabled()` checks for `NEO4J_URI` and
`NEO4J_PASSWORD` in the environment; if unset, or if the database is unreachable,
`recommend_products` returns `[]` and callers get exactly the same response shape they would
with the graph configured, just empty. The rule-based recommender in layer 1 is completely
unaffected either way. `GET /graph/status` reports `{enabled, connected}` so the frontend can
decide whether to render the graph-powered section at all; it does not error or block on it.

## 7. HTTP API surface

`backend/api.py`, all JSON, no auth (single-RM demo).

| Method | Path | Returns |
|---|---|---|
| GET | `/me` | The logged-in RM's display name. |
| GET | `/sectors` | Sorted list of sectors present in the book. |
| GET | `/portfolios` | All client portfolios (excludes the reference book). |
| GET | `/clients` | Full client accounts: profile, holdings, sector breakdown, performance, suitability, insights, suggested sector. |
| GET | `/overview` | Firm-wide roll-up: KPIs, action items, book performance, risk distribution, asset/sector allocation, top holdings, largest clients. |
| GET | `/products` | Investable universe grouped by asset class. |
| GET | `/securities` | Flat investable universe, name-sorted, for the holdings editor's picker. Unlike `/products` it includes cash and already-held names. |
| GET | `/profile-options` | The behavioral-profile vocabulary the forms offer, plus `scoring_fields`: which of them actually drive product ranking. Served from the backend so the options cannot drift from the keyword rules that score them. |
| POST | `/clients` | Add a client. Clones a template portfolio's asset mix scaled to the new AUM, computes risk with the shared formula, accepts an optional behavioral profile. Writes to the overlay. |
| PUT | `/clients/{portfolio_id}/holdings` | Replace a client's holdings. Raw weights are normalized, NAV is preserved unless overridden, risk is recomputed. Works on seeded clients too. |
| PUT | `/clients/{portfolio_id}/profile` | Fill in or correct persona and psychographics. Merges rather than replaces. Returns the re-ranked `product_suggestions` as proof the edit reached the recommender. |
| DELETE | `/clients/{portfolio_id}` | Remove a runtime-added client. Refuses seeded ones with 400, since nothing at runtime writes to the seed dataset. |
| GET | `/news/categories` | The seven news categories. |
| GET | `/news/feed?category=&force=` | Cached briefing: TL;DR, key points, key stats, affected clients with talking points, citations. |
| POST | `/lens/run` | Run the research lens for a sector; returns narrative, citations, and all impact engines. |
| POST | `/talking-points` | Talking points for one client + sector. |
| GET | `/graph/status` | `{enabled, connected}` for the optional Neo4j knowledge graph. |
| GET | `/clients/{portfolio_id}/graph-suggestions` | Graph-based product suggestions for one client; `{enabled: false, suggestions: []}` if the graph is not configured. |
| GET | `/clients/{portfolio_id}/graph-view` | Renderable graph (nodes/edges) for the Product Fit tab: client, top holdings, asset classes, both recommendation layers, and the single best product to highlight. |
| GET | `/graph/overview` | Firm-wide Product Fit view: every client's best-match product, flowing client -> asset class -> product, plus a top-products leaderboard. |

## 8. Caching

Both LLM-backed surfaces (News Feed and Analysis) follow the same cache-then-refresh model, so a
repeat visit is instant while a manual control always forces a fresh live pull.

- **Server**: an in-process dict caches each news category for a TTL; `force=true` bypasses it.
  This keeps repeated tab opens from re-running the pipeline.
- **News Feed client cache**: each fetched category is persisted to `localStorage` (keyed
  `prism_news_cache_v3`), so opening the tab is instant. Content older than 12 hours refreshes in
  the background on open; a manual Reload button forces a fresh call at any time. The key is
  versioned so a schema change discards stale caches.
- **Analysis client cache**: each run is one live call per (client, sector), so results are
  cached in `localStorage` (keyed `prism_analysis_cache_v1`) under a `<portfolio_id>::<sector>`
  key. Re-opening or re-selecting a cached combination shows instantly; a per-result Refresh
  button re-runs live, and results older than 12 hours re-run on demand. A failed refresh keeps
  the cached result on screen.

## 9. Tech stack and ops

- **Backend**: Python 3.13, FastAPI, uvicorn, `anthropic` SDK, `python-dotenv`, `neo4j` driver
  (optional dependency, section 6). A Streamlit script (`app.py`) exists for a quick standalone
  view.
- **Frontend**: Next.js 16 (App Router, Turbopack), React 19, TypeScript 5, `@number-flow/react`
  for animated stats. Runs as a production build (`next build` + `next start`) for stability.
- **Config**: `ANTHROPIC_API_KEY` plus an optional `PM_NAME`, and optionally `NEO4J_URI` /
  `NEO4J_USERNAME` / `NEO4J_PASSWORD` for the knowledge graph, all from `backend/.env`. `.env` is
  gitignored; the public repo ships only `.env.example` with placeholders.
- **Tests**: 135 pytest tests across the dataset, entity linker, extraction, impact engines, and
  the API, including the runtime-edit overlay (section 4.1) and the graph endpoints'
  graceful-degradation path with no Neo4j configured. The deterministic core is fully covered; live
  LLM calls and a real Neo4j connection are exercised by manual runs rather than mocked.

### 9.1 Visual design system

The UI follows the design language of the Perplexity Ads deck. The values were **measured from
that PDF** (content-stream colour operators, font resources, `Tf` size operators), not eyeballed
from screenshots.

**Palette.** Four colours carry the whole deck, and they carry the app:

| Token | Hex | Role | Uses in deck |
|---|---|---|---|
| `--bg` | `#FCFCF9` | Paper. Warm off-white page ground, never pure white | 34 |
| `--text` / `--ink` | `#13343B` | Peacock. The "ink" — body text and dark hero tiles, in place of black | 144 |
| `--accent` | `#20808D` | Turquoise. The single accent | 30 |
| `--on-ink` | `#FFFFFF` | Type on dark tiles | 82 |

The argument is restraint: one accent, spent only on interactive chrome and single-series data.
Dark mode is *selected*, not inverted — its surfaces are steps down the same peacock hue, with
`#13343B` used verbatim as `--surface`.

**Typography.** The deck pairs a neutral grotesk (FK Grotesk, in Thin/Light/Regular/Bold) with
Instrument Serif Italic used for exactly one emphasised word inside a grotesk line ("Search like
*never* before"). FK Grotesk is commercially licensed and cannot ship here, so **Inter** stands in:
same neo-grotesque genre, and it has the 200–300 weights the display treatment depends on.
Instrument Serif is openly licensed, so that half is exact. The flourish is applied on one headline
only — the deck itself uses it on 2 of 33 slides, and overusing it would break the restraint that
makes it work.

Type runs 18pt→180pt on the deck's 1440pt slide, a 10× range. App UI cannot go that far, but
`--display-1/2/3` encode the principle: a far wider range than typical dashboard type, with
**weight falling as size climbs** (`--weight-display: 250`). Nothing large is ever bold.

**Figures.** The deck's stats slide sets the pattern, and it inverts the usual KPI card: label
**above** the number, in sentence case at body size; the figure huge and light-weight; and *no card
at all* — no border, no fill, no shadow, grouped by whitespace. Big numbers are set in the grotesk
at Light, not in a bold monospace. Mono survives only for tickers and ids, where cell alignment
genuinely helps.

**Charts.** The deck's bar chart paints every bar the same turquoise and lets the row label carry
identity — no gridlines, no axis, no value labels on marks, one hairline baseline. Applied here:
any mark that is already directly labelled takes the accent, which is why the 14 sector-exposure
rows went from 14 hues to one. That also retires a genuine anti-pattern, since no categorical
palette keeps 14 hues distinguishable.

Categorical hues are therefore spent only where a mark *cannot* be labelled in place — the
allocation donut. Those steps (`--cat-1…6`, `--cat-neutral`) are validator output, not hand-picked:
both modes PASS the lightness band, chroma floor, protan/deutan adjacent separation,
normal-vision floor, and contrast-vs-surface checks.

| Mode | Surface | Worst adjacent CVD ΔE | Normal-vision floor |
|---|---|---|---|
| Light | `#FCFCF9` | 11.6 (protan) | 20.7 |
| Dark | `#13343B` | 9.3 (deutan) | 16.3 |

The previous palette's worst adjacent pair was ΔE 8.6, so this is a measurable improvement rather
than a lateral restyle.

Two deliberate departures from the deck:

- **Status colours keep their own hues.** Positive/negative and the five risk tiers encode meaning;
  the deck has no equivalent to borrow, and collapsing them into the accent would destroy
  information. They are re-harmonised toward peacock, not replaced.
- **`--accent` is not a categorical slot.** `#20808D` FAILS the categorical chroma floor
  (OKLCH C = 0.086 against a 0.10 floor) — at that saturation it reads as grey once it must be told
  apart from other hues. It is perfect as a lone accent, where there is nothing to distinguish it
  from. The donut's teal is `#008C9E`: same cyan-teal hue, pushed over the floor.

### Running locally

```
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env          # add ANTHROPIC_API_KEY (and NEO4J_* if using the graph)
python build_dataset.py       # generate prism_data.json
python build_graph.py         # optional: populate Neo4j (needs NEO4J_* in .env)
uvicorn api:app --port 8000

# Frontend
cd frontend
npm install
npm run build && npm run start   # http://localhost:3000
```

Omitting `NEO4J_*` and the `build_graph.py` step is fully supported: the app runs identically,
just without the graph-powered "Similar clients also hold" section.

## 10. Roadmap

- **Real market data**: swap illustrative performance for live historical NAV via one of the free
  market-data APIs in section 2 (Finnhub / Marketaux / NewsAPI), reusing the existing linking and
  roll-up stages.
- **Deepen the knowledge graph**: add `SIMILAR_TO` client-similarity edges precomputed offline
  (rather than the on-query life-stage/risk-tier match), and a `CO_HELD_WITH` product-product edge
  for "clients who hold X also hold Y" market-basket suggestions.
- **Per-(client, sector) analysis cache** so repeated Analysis runs are instant.
- **One-click meeting prep**: assemble a client's profile, performance, relevant news, and talking
  points into a single brief.
- **Client-facing change alerts**: what moved in a client's book since last contact.

## 11. Open questions

- How much of the performance layer should be driven by real NAV history versus staying
  illustrative for the demo?
- Should the "you vs a normal book" reference be the fixed 60/40, or a peer-group average?
- What is the right cache TTL for live news given how fast the Indian market news cycle moves?
- Should the graph's `PREFERS` affinity scores stay derived from the same rules as the Python
  recommender, or should the graph eventually own a richer, independently-tunable scoring model?
