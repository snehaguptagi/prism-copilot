# PRISM - Investment Research & Portfolio Insight Copilot

[![CI](https://github.com/snehaguptagi/prism-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/snehaguptagi/prism-copilot/actions/workflows/ci.yml)

A portfolio-aware research assistant for buy-side relationship managers, focused on the
Indian market. It turns live market news into cited, book-specific insight: which of your
clients a development actually touches, by how much, and what to tell them.

> Decision-support tool. Not investment advice, not a trading system. Every surfaced number
> is computed deterministically and every claim is grounded in a cited source.

## Repository layout

| Folder | What it is |
|---|---|
| [`backend/`](./backend) | FastAPI + the market-insight pipeline (entity linking, deterministic roll-ups, direction/factor engine, news briefing, talking points). Python. |
| [`frontend/`](./frontend) | Next.js + TypeScript app: Overview, Clients, Portfolio Analysis, News Feed, Products. |
| [`docs/`](./docs) | Design docs describing the project as built: the [PRD](./docs/PRD.md) (product) and [LLD](./docs/LLD.md) (technical design + the external APIs used). |

## Design docs

Both docs in [`docs/`](./docs) describe PRISM as actually built, each opening with an overall picture of the project:

- **[Product Requirements Document (PRD.md)](./docs/PRD.md)** - overall picture, problem, the RM and the 16 client personas, the five feature surfaces, functional and non-functional requirements, compliance guardrails, and success criteria.
- **[Low-Level Design (LLD.md)](./docs/LLD.md)** - overall architecture, **the external APIs used** (the Anthropic Claude API with its hosted web-search tool, plus the free market-data APIs considered), data model, the research-to-insight pipeline, deterministic engines, the HTTP API surface, caching, tech stack, and roadmap.

The running system uses a single external API: the Anthropic Claude API, including its hosted `web_search_20250305` tool for grounded, cited market research. Free market-data APIs (Finnhub, Marketaux, NewsAPI) were evaluated during scoping and are documented in the LLD as the drop-in path for real price/news feeds, but are not used in the current build.

## What it does

- **Overview** - firm-wide book summary (AUM, risk spread, asset/sector allocation, top holdings), all computed from real holdings.
- **Clients** - a roster of 16 distinct client personas, from a ₹38 lakh young trader to a ₹46 crore business promoter, each with a full profile: behavioral psychographics, relationship insights, portfolio metrics, holdings, performance vs the Nifty, a suitability check, and a PM-to-client communication log with the next action due.
- **Portfolio Analysis** - pick a client's book, run live market analysis on its dominant exposure, get exposure vs. a normal book plus tailored talking points.
- **News Feed** - categorized live market news reduced to a one-line TL;DR, clean key-point bullets, and per-client talking points. Cached so it does not reload on its own; manual Reload button.
- **Products** - the investable universe the desk can offer, grouped by asset class.
- **Product Fit** - a visual map, per client, of their holdings, preferences, and the products worth raising with them, with the single strongest pick highlighted. Suggestions are matched to each client's stated preferences (goal, horizon, loss aversion, life stage) and risk mandate; an optional knowledge graph adds a second, similar-client layer on top. The app works identically without it.
- **Light and dark theme** - a toggle in the top bar; the choice persists across visits and otherwise follows the system preference.

## Adding and editing clients

The 16 personas are demo data, and they are also the starting point for your own. Adding a client
never asks you to type a portfolio from scratch:

1. **Add a client** from the Clients tab. You give the client-level facts (name, mandate, initial
   AUM) and pick a **starting strategy** - one of the existing books, whose asset mix is cloned and
   rescaled to your client's AUM. Optionally answer the four preference questions (goal, horizon,
   loss aversion, life stage); those are what Product Fit ranks against, so a client without them
   gets suggestions that can only fill allocation gaps.
2. **Edit holdings** on the client's Holdings tab: adjust weights, add securities from the full
   investable universe, remove positions. Weights are normalized on save, so they need not total
   exactly 100, and AUM is held constant. Risk tier, volatility and concentration are recomputed by
   the same `compute_portfolio_risk` formula used for every seeded client, so an edited book stays
   directly comparable to the demo ones.
3. **Edit the profile** on the Profile tab, for seeded clients as well as your own.

All of this is written to `backend/prism_overlay.json`, never to `prism_data.json`. That split is
deliberate: `python build_dataset.py` can regenerate the demo dataset at any time without destroying
your work, and deleting the overlay resets the app to the shipped 16 personas. The overlay is
gitignored, like `.env`. Clients you added can be removed from the app; seeded ones cannot, since
nothing at runtime writes to the seed dataset.

## Core design principles

- **Portfolio-aware grounding is the moat.** Every insight is linked to actual holdings.
- **Deterministic math, LLM narration.** Exposure, NAV impact, and factor sensitivity are plain arithmetic; the model only phrases them, it never computes numbers.
- **Citations mandatory.** Claims without a supporting source are suppressed.
- **Decision-support only.** No buy/sell/hold guidance, no trade execution.

## Running locally

### Backend
```bash
cd backend
pip install -r requirements.txt
# copy .env.example to .env and add your ANTHROPIC_API_KEY
python build_dataset.py          # generate the synthetic India dataset
uvicorn api:app --port 8000
```

### Optional: Neo4j knowledge graph (product recommendation)

Adds a second, graph-powered layer to product suggestions on top of the always-on rule-based
recommender. Entirely optional; the app runs identically without it.

```bash
# in backend/.env, also set:
#   NEO4J_URI=neo4j+s://<id>.databases.neo4j.io   (or bolt://localhost:7687 for local)
#   NEO4J_USERNAME=neo4j
#   NEO4J_PASSWORD=<your password>
python build_graph.py            # populates the graph from prism_data.json
```

### Frontend
```bash
cd frontend
npm install
npm run dev                      # http://localhost:3000
```

The frontend expects the backend at `http://localhost:8000` (override with `NEXT_PUBLIC_API_BASE`).

## Deploying

See **[docs/DEPLOY.md](./docs/DEPLOY.md)**. In short: the frontend deploys to Vercel
cleanly with `NEXT_PUBLIC_API_BASE` set at build time, but the backend needs a host
with a writable disk and a long request timeout (Render, Railway, Fly, a VM) — on
Vercel's read-only filesystem every runtime edit fails, and the 55-second research
call does not fit a serverless timeout. Rotate the Anthropic key and put the open
API behind auth or a rate limit before exposing it publicly.

## Tests

```bash
cd backend
python -m pytest tests/ -q       # deterministic core is fully unit-tested
```

## Continuous integration

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs the deterministic
backend test suite on every push and pull request. It needs no API key and spends
no Anthropic credits.

An optional, manual-only `live-smoke` job makes one real grounded research call to
verify the pipeline end to end. It reads the key from an encrypted GitHub Actions
secret, never from the repo. To enable it, add the secret once (the value stays
encrypted and is never printed in logs):

- **GitHub UI:** repo Settings > Secrets and variables > Actions > New repository
  secret, name `ANTHROPIC_API_KEY`.
- **CLI:** `gh secret set ANTHROPIC_API_KEY` (prompts for the value, hidden input).

Then trigger it from the Actions tab via "Run workflow". Normal pushes never run it,
so CI stays free.

## Data note

All client, portfolio, and communication data is synthetic, built to demonstrate the workflow.
It does not represent real people or real accounts.
