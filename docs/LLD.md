# PRISM - Low-Level Design (LLD)

> Technical design of PRISM as built: architecture, the external APIs used, data model, the
> research-to-insight pipeline, the deterministic engines, the HTTP API surface, tech stack, and
> how to run it. See the [Product Requirements Document](PRD.md) for product scope.

---

## 1. Overall picture

PRISM is a two-process web app plus a synthetic data generator:

```
                         build_dataset.py
                    (synthetic India dataset gen)
                                 |
                                 v
                        backend/prism_data.json
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
  desks, portfolios, securities, holdings, risk, and a benchmark. The backend loads it at startup.

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
  the classification pass, and results are cached (see section 7).

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

## 6. HTTP API surface

`backend/api.py`, all JSON, no auth (single-RM demo).

| Method | Path | Returns |
|---|---|---|
| GET | `/me` | The logged-in RM's display name. |
| GET | `/sectors` | Sorted list of sectors present in the book. |
| GET | `/portfolios` | All client portfolios (excludes the reference book). |
| GET | `/clients` | Full client accounts: profile, holdings, sector breakdown, performance, suitability, insights, suggested sector. |
| GET | `/overview` | Firm-wide roll-up: KPIs, action items, book performance, risk distribution, asset/sector allocation, top holdings, largest clients. |
| GET | `/products` | Investable universe grouped by asset class. |
| GET | `/news/categories` | The seven news categories. |
| GET | `/news/feed?category=&force=` | Cached briefing: TL;DR, key points, key stats, affected clients with talking points, citations. |
| POST | `/lens/run` | Run the research lens for a sector; returns narrative, citations, and all impact engines. |
| POST | `/talking-points` | Talking points for one client + sector. |

## 7. Caching

- **Server**: an in-process dict caches each news category for a TTL; `force=true` bypasses it.
  This keeps repeated tab opens from re-running the pipeline.
- **Client**: the News Feed persists each fetched category to `localStorage` (keyed
  `prism_news_cache_v3`), so opening the tab is instant and never auto-refetches. A manual Reload
  button forces a fresh call. The key is versioned so a schema change discards stale caches.

## 8. Tech stack and ops

- **Backend**: Python 3.13, FastAPI, uvicorn, `anthropic` SDK, `python-dotenv`. A Streamlit
  script (`app.py`) exists for a quick standalone view.
- **Frontend**: Next.js 16 (App Router, Turbopack), React 19, TypeScript 5, `@number-flow/react`
  for animated stats. Runs as a production build (`next build` + `next start`) for stability.
- **Config**: single `ANTHROPIC_API_KEY` plus an optional `PM_NAME`, both from `backend/.env`.
  `.env` is gitignored.
- **Tests**: 88 pytest tests across the dataset, entity linker, extraction, impact engines, and
  the API. The deterministic core is fully covered; live LLM calls are exercised by manual runs
  rather than mocked.

### Running locally

```
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env          # add ANTHROPIC_API_KEY
python build_dataset.py       # generate prism_data.json
uvicorn api:app --port 8000

# Frontend
cd frontend
npm install
npm run build && npm run start   # http://localhost:3000
```

## 9. Roadmap

- **Real market data**: swap illustrative performance for live historical NAV via one of the free
  market-data APIs in section 2 (Finnhub / Marketaux / NewsAPI), reusing the existing linking and
  roll-up stages.
- **Per-(client, sector) analysis cache** so repeated Analysis runs are instant.
- **One-click meeting prep**: assemble a client's profile, performance, relevant news, and talking
  points into a single brief.
- **Client-facing change alerts**: what moved in a client's book since last contact.

## 10. Open questions

- How much of the performance layer should be driven by real NAV history versus staying
  illustrative for the demo?
- Should the "you vs a normal book" reference be the fixed 60/40, or a peer-group average?
- What is the right cache TTL for live news given how fast the Indian market news cycle moves?
