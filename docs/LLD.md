# PRISM - Low-Level Design (LLD)

> Technical design, data model, pipeline, and API surface for PRISM.
> This is Part B (Design) and Part C (Plan) of the original scoping document. See the [Product Requirements Document](PRD.md) for product scope.

---

## System architecture

A layered pipeline: sources flow through ingestion into a knowledge layer that is enriched with holdings context at index time, so "what affects my book" is a first-class filter rather than a post-hoc computation.

## Component design

| Component | Responsibility | Key decisions |
| --- | --- | --- |
| Ingestion svc | Fetch, parse, normalise, dedupe source documents | Pluggable loaders per source; idempotent; near-dup detection by minhash |
| Entity linker | Resolve mentions to the firm's securities master | Hybrid: symbolic dictionary/gazetteer first, LLM disambiguation on ambiguity; confidence scored |
| Indexer | Chunk, embed, and attach holding/sector metadata | Metadata written at index time so linkage is a filter, not a join at query time |
| Retriever | Fetch relevant chunks under entitlement | Hybrid dense + keyword; entitlement + fund/date filters applied pre-rank |
| Orchestrator | Summarise, link, answer, and verify claims | Tiered models; verifier pass rejects ungrounded claims |
| Roll-up engine | Compute NAV impact, sector and factor exposure | Deterministic, not LLM; reads from portfolio store |
| Digest/alert svc | Scheduled digests and threshold alerts | Per-user materiality thresholds |
| Audit svc | Immutable log of queries, sources, outputs | Append-only; feeds compliance review |

## Data model

Core entities. Portfolio, desk, and entitlement are first-class from day one to support multi-desk GCC delivery.

```
# Security master (linkage target)
Security { security_id, primary_ticker, name, aliases[], isin,
           parent_id?, adr_of?, sector, industry, country }

# Portfolio holdings, per desk
Holding  { holding_id, portfolio_id, security_id, weight,
           market_value, as_of_date }
Portfolio{ portfolio_id, desk_id, name, base_ccy, mandate }
Desk     { desk_id, tenant_id, name }

# Ingested content
Document { doc_id, source_type, title, published_at, url,
           tenant_scope, raw_text, checksum }
Chunk    { chunk_id, doc_id, span, text, embedding,
           linked_security_ids[], sectors[], link_confidence }

# Derived insight
Insight  { insight_id, event_key, summary, claims[],
           affected_holdings[], nav_impact_pct, created_at }
Claim    { claim_id, text, source_doc_id, source_span,
           faithfulness_score }

# Access & audit
Entitlement{ user_id, desk_id, source_types[], portfolio_ids[] }
AuditEvent { event_id, user_id, action, query, shown_sources[], ts }
```

## Ingestion pipeline

1. **Fetch.** Source-specific loaders pull raw content on schedule or webhook. Idempotent by checksum.
2. **Parse & normalise.** Convert to the common `Document` schema; strip boilerplate; extract publish date and title.
3. **Dedupe.** Near-duplicate detection (minhash/shingling) collapses the same story across wires into one `event_key`.
4. **Entity link.** Run the linker (§17); attach `linked_security_ids` and confidence.
5. **Chunk & embed.** Finance-aware chunking that keeps tables and speaker turns intact; embed; write holding/sector metadata onto each chunk.
6. **Index.** Upsert into the vector store; emit an ingest event for downstream digest/alert.

## Entity linking (the moat)

This is the riskiest and most valuable component. A hybrid design balances precision and cost:

1. **Candidate generation (symbolic).** A gazetteer built from the securities master (names, tickers, aliases, common misspellings) does a high-recall first pass. Cheap and deterministic.
2. **Disambiguation (LLM, only when needed).** When a mention is ambiguous (shared names, ticker collisions, parent vs subsidiary), an LLM resolves it using surrounding context. Reserved for the hard cases to control cost.
3. **Relationship expansion.** Resolve subsidiary-to-parent, ADR-to-ordinary, and supply-chain adjacency so an event on a private supplier can still flag a held customer.
4. **Confidence + fail-closed.** Each link carries a score. Below threshold, the insight is shown without the holding link and the uncertainty is surfaced, never a confident guess.

Prove this on 20 hand-labelled documents before building any UI. Target > 90% precision. If it fails here, the value proposition shifts and the roadmap must adapt.

## Retrieval & RAG

- **Hybrid retrieval.** Dense (embeddings) + sparse (keyword/BM25) to catch both semantic and exact-ticker matches.
- **Pre-rank filtering.** Entitlement, fund, entity, and date filters applied before ranking, so results are always in-scope and permitted.
- **Portfolio-scoped retrieval.** Because chunks carry `linked_security_ids`, "insights about my holdings" is a metadata filter, cheap and exact.
- **Re-ranking.** Cross-encoder or LLM re-rank on the shortlist for precision on the final context window.
- **Citation binding.** Every retrieved chunk keeps its `doc_id` + `span` so the generator can cite exactly.

## LLM orchestration

Tiered model routing keeps cost sane without sacrificing the reasoning that matters.

| Task | Model tier | Why |
| --- | --- | --- |
| Bulk document summarisation | Fast / cheaper tier | High volume, low reasoning depth |
| Entity disambiguation | Mid tier | Context reasoning on hard cases only |
| Book-linked reasoning & Q&A | Top tier (Opus-class) | The judgement step users trust |
| Claim verification | Mid / top tier | Checks each claim against its source span |

#### Grounding & verification loop

1. Generate answer with inline citations bound to retrieved spans.
2. Verifier pass checks each claim is supported by its cited span; unsupported claims are dropped.
3. If coverage drops below threshold, respond with what is supported and flag the gap rather than filling it.

## Portfolio roll-up engine

Deliberately **deterministic, not LLM-driven**. Given an event with linked securities, it computes, from the portfolio store:

- **Affected holdings** and each position's weight.
- **NAV impact** = sum of weights of touched held names, per fund.
- **Sector / geography breakdown** of the exposure.
- **Risk shifts** (Should tier): concentration and factor-tilt deltas implied by the event.

Keeping this arithmetic outside the LLM makes the numbers exact, reproducible, and auditable. The LLM narrates them; it does not compute them.

## API surface

```
POST /ingest              # queue a document or source pull
GET  /events?fund=&since=   # material events, ranked by NAV impact
GET  /events/{id}          # cited summary + affected holdings
POST /ask                 # grounded Q&A; body: query + filters
GET  /holdings/{fund}/insights  # book-scoped feed
GET  /digest/{user_id}     # personalised digest
POST /alerts/rules        # set materiality thresholds
GET  /oversight/heatmap    # CIO firm-wide exposure view
GET  /audit?user=&range=   # compliance audit trail
```

Every response that carries a claim also carries its citations (`doc_id`, `span`, `url`) and, where relevant, a `link_confidence`.

## Evaluation harness

Trust is measurable, so measure it continuously. The eval set is versioned and grows with each pilot finding.

| Eval | Method | Gate |
| --- | --- | --- |
| Linkage precision/recall | Hand-labelled mention→holding set | Precision > 92% |
| Citation faithfulness | Claim vs cited span, LLM-judge + spot human audit | > 98% |
| Summary quality | Rubric scoring on a fixed doc set | Human-acceptable > 90% |
| Hallucination rate | Injected unanswerable questions | Refusal > 95% |
| Latency & cost | Load test on representative corpus | Meets §9 NFRs |

## Tech stack & ops

#### Prototype stack

- **Language:** Python
- **UI:** Streamlit (fast to a demo)
- **LLM:** Claude, tiered (Opus-class for reasoning)
- **Vector store:** Chroma / FAISS
- **Portfolio store:** SQLite/Postgres
- **Orchestration:** Lightweight Python services

#### Production evolution

- **UI:** React/typed web app for entitlements & scale
- **Vector store:** managed, multi-tenant
- **Data:** Postgres + object storage, tenant-isolated
- **Ingestion:** queue-based workers, independent scaling
- **Observability:** eval dashboards, cost + latency tracing
- **Deploy:** tenant-isolated, configurable residency

## Roadmap

## Open questions

- Which asset class and region for the pilot book (US equities, India equities, multi-asset)? It shapes the securities master and news sources.
- What is the firm's system of record for holdings, and how do we get a daily feed?
- What is the acceptable latency/cost envelope per analyst per day?
- Which licensed news provider has redistribution terms compatible with the product?
- What is the compliance line on surfacing internal research alongside external content?
- Is the first buyer a single desk or the CIO office? It changes which oversight features move up the roadmap.
