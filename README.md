# PRISM - Investment Research & Portfolio Insight Copilot

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
| [`docs/`](./docs) | Product and technical scoping: the [PRD](./docs/PRD.md) (Part A, product) and [LLD](./docs/LLD.md) (Parts B and C, design and plan). |

## Design docs

The full scoping that this MVP is built from lives in [`docs/`](./docs):

- **[Product Requirements Document (PRD.md)](./docs/PRD.md)** - problem, personas, goals, feature scope, user journeys, functional and non-functional requirements, compliance guardrails, and the risk register.
- **[Low-Level Design (LLD.md)](./docs/LLD.md)** - system architecture, component design, data model, ingestion pipeline, entity linking, retrieval and RAG, LLM orchestration, the portfolio roll-up engine, API surface, evaluation harness, tech stack, roadmap, and open questions.

The docs describe the general buy-side copilot. What ships in this repo is the concrete India-only, relationship-manager instantiation of that scope: a single-tenant demo over synthetic Indian portfolios, with the entity-linking and deterministic roll-up ideas from the LLD implemented end to end.

## What it does

- **Overview** - firm-wide book summary (AUM, risk spread, asset/sector allocation, top holdings), all computed from real holdings.
- **Clients** - a roster of 16 distinct client personas, from a ₹38 lakh young trader to a ₹46 crore business promoter, each with a full profile: behavioral psychographics, relationship insights, portfolio metrics, holdings, performance vs the Nifty, a suitability check, and a PM-to-client communication log with the next action due.
- **Portfolio Analysis** - pick a client's book, run live market analysis on its dominant exposure, get exposure vs. a normal book plus tailored talking points.
- **News Feed** - categorized live market news reduced to a one-line TL;DR, clean key-point bullets, and per-client talking points. Cached so it does not reload on its own; manual Reload button.
- **Products** - the investable universe the desk can offer, grouped by asset class.

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

### Frontend
```bash
cd frontend
npm install
npm run dev                      # http://localhost:3000
```

The frontend expects the backend at `http://localhost:8000` (override with `NEXT_PUBLIC_API_BASE`).

## Tests

```bash
cd backend
python -m pytest tests/ -q       # deterministic core is fully unit-tested
```

## Data note

All client, portfolio, and communication data is synthetic, built to demonstrate the workflow.
It does not represent real people or real accounts.
