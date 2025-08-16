# Deep Research Agent — Comprehensive Planning Document

2025-08-15 20:18:05 - Initialized from docs/prd.md and Memory Bank.

This document operationalizes the PRD into an executable plan: architecture, specifications, APIs, data models, UX, testing, observability, security, ops, performance, cost, risks, backlog, and milestones. It is the single source of truth for Stage 1–4 delivery.

References:
- PRD: [docs/prd.md](docs/prd.md)
- Memory Bank:
  - [memory-bank/productContext.md](../memory-bank/productContext.md)
  - [memory-bank/activeContext.md](../memory-bank/activeContext.md)
  - [memory-bank/progress.md](../memory-bank/progress.md)
  - [memory-bank/decisionLog.md](../memory-bank/decisionLog.md)
  - [memory-bank/systemPatterns.md](../memory-bank/systemPatterns.md)

---

## 1) Executive summary

Build a fast, reliable deep-research agent that plans, searches, reads, verifies, and writes cited briefs. Ship an MVP in Python with Streamlit, using Cerebras GPT-OSS-120B through OpenAI-compatible APIs. Scale through robustness, orchestration, and a polished web app, optimizing for throughput, reliability, observability, and cost.

---

## 2) Product scope and requirements traceability

- Outputs: 800–1,200 word analyst-grade briefs in Markdown with numbered citations and a References section.
- Claims policy: All non-obvious claims must have ≥1 source; target ≥2 for 60%+ by Stage 4.
- Tooling: web_search, fetch_url (HTML), parse_pdf; enforce robots.txt.
- Limits: max search rounds, per-domain caps, request timeouts; configurable via config file and UI.
- Observability: token counts, time, source counts, domain diversity; logs and traces.

Traceability matrix (high-level):
- PRD Goals → Sections in this plan
  - Analyst-grade briefs → Writer spec, Evaluation plan
  - Claim coverage enforcement → Verifier spec, Evaluation metrics
  - Speed/cost visibility → Observability, Performance, Cost model
  - MVP limits → MVP scope, Acceptance criteria

---

## 3) System architecture

Runtime path (MVP → Scale):
- Client UI (Streamlit) → Backend service (/run) → Agent loop (Planner → Searcher → Reader → Analyst → Verifier → Writer) → Cerebras chat API (OpenAI-compatible) + search/fetch tools → SQLite cache (Stage 2+) → Storage (reports)
- Model: gpt-oss-120b via Cerebras Inference Cloud (OpenAI-compatible). Configure client with base_url and API key.

Key architectural tenets:
- Deterministic orchestration with explicit tool-call boundaries.
- Caching-first I/O; robust retries/backoff; per-domain rate limits (Stage 2).
- Explicit state objects flowing across components to enable tracing and evaluation.
- Pluggable providers (search engines; later orchestration engines).

---

## 4) Component specifications

Note: No code here to keep this document language-agnostic.

- Planner
  - Input: topic, constraints, prior knowledge (optional)
  - Output: sub-questions and initial search queries; stopping criteria
  - Rules: generate diverse queries (operator variants, site/domain filters if constraints provided)
- Searcher
  - Input: queries, k, provider config
  - Output: SearchResult[] {title, url, snippet}
  - Rules: enforce per-domain caps, normalize URLs, dedupe at URL level
- Reader
  - Input: URLs
  - Output: Document[] {url, title, text, source_meta}
  - Rules: fetch with headers; respect robots.txt; extract main content (HTML), parse PDF; chunk (by tokens)
- Analyst
  - Input: Chunks grouped by document; plan/sub-questions; constraints
  - Output: claims, interim citations, synthesis notes
  - Rules: ensure traceability for claim → source
- Verifier
  - Input: Draft sections, claims, citations, corpus
  - Output: unsupported claims list; follow-up queries; remediation suggestions
  - Rules: zero orphan claims before finalization
- Writer
  - Input: verified outline/sections/citations
  - Output: final Markdown brief + References list; optional JSON report

Cross-cutting:
- Dedupe: URL normalization, text SimHash/MinHash (Stage 2)
- Quality gate: domain allow/deny, language filter, length thresholds (Stage 2)
- Caching: SQLite for pages and traces (Stage 2)
- Orchestration: LangGraph for explicit plan/tool/verify loops (Stage 3)

---

## 5) Data model (Stage 2+ formalization)

- SearchResult { title, url, snippet }
- Document { url, title, text, source_meta }
- Chunk { doc_url, text, hash, tokens }
- Claim { id, text, type, confidence }
- Citation { claim_id, urls[] }
- Report { topic, outline, sections[], citations[], references[] }
- TraceEvent { ts, kind, payload }
- Config { search_provider, k, max_rounds, caps, timeouts }

Notes:
- In Stage 1, typed dicts are sufficient; Stage 2 moves to Pydantic v2 for validation and JSON export stability.
- Hashes used for dedupe and cache keys (e.g., sha256 of normalized text).

---

## 6) Tooling and provider interfaces

- web_search
  - Inputs: query (string), k (int), provider (enum), date_range (optional)
  - Output: SearchResult[]
- fetch_url
  - Inputs: url (string), timeout, headers
  - Output: { html or text, meta }
- parse_pdf
  - Inputs: url or bytes
  - Output: text + meta

Provider abstraction:
- Search providers: DuckDuckGo (default for MVP) → Tavily/Bing/Brave plugs later
- Model provider: OpenAI-compatible pointing at Cerebras; expose model, base_url, api_key

---

## 7) API specification

- POST /run
  - Body: { topic, constraints?, config? }
  - Returns: { report_md, report_json (optional in MVP), metrics: { duration_s, tokens_in, tokens_out, cost_est } }
- GET /runs/:id
  - Returns: prior result + trace (Stage 3)

HTTP behaviors:
- Idempotency for /run per topic+config hash (if cached and allowed).
- Request IDs in headers; map to traces.

---

## 8) UX flows

MVP (Streamlit):
- Text area for topic
- Optional: constraints panel (date range, include/exclude domains)
- “Run” button
- Status log (tool calls, pages fetched, token/costs)
- Markdown output with citations and References
- Download buttons: .md (and .json later)

Stage 3–4 (Next.js):
- Left: plan/logs/errors; Right: live draft + citations
- Evidence map: claims vs sources; coverage heatmap
- Inline citation preview on hover
- Keyboard shortcuts: Cmd/Ctrl+Enter to run

---

## 9) Observability

- Logs: structured JSON; include request_id, topic_hash, timings, tokens, sources count, cache hits/misses
- Traces: TraceEvent stream persisted to SQLite (Stage 2) and optionally exported via OpenTelemetry (Stage 3)
- Metrics: evaluation harness metrics (time, tokens, sources, domain diversity, dead-link rate, claim coverage, duplication)

---

## 10) Security and compliance

- Respect robots.txt and site terms
- Do not store raw pages beyond cache; store extracted text + URL + hash
- Secret management via environment variables; never hardcode
- PII: avoid collecting; encrypt uploads at rest; redact sensitive URL params in logs

---

## 11) Operations

- Configuration: .env for keys and caps
- Concurrency/backpressure: limit concurrent runs; queue overflow with clear errors
- Cost guardrails: per-run token ceilings; org caps (Stage 4)
- Health checks: provider reachability; search provider fallback/rotation

---

## 12) Performance strategy

- MVP latency target: ≤6 minutes for 2–3 search rounds
- Stage 4 target: 60–90 seconds typical via:
  - Parallel search+fetch
  - Aggressive caching with warm starts
  - Streaming at ~3,000 tok/s on Cerebras
  - Early-write while reading continues (progressive drafting)

---

## 13) Cost model

- Track tokens_in/tokens_out, duration_s, per-run cost estimate
- Pre-run cost estimate: planned rounds × avg tokens × unit cost
- Guardrails: ceiling enforced; user-visible

---

## 14) Risks and mitigations

- Paywalls/anti-bot → summaries, public alternates, user PDFs
- Source spam → domain quality scores, allow/deny
- Hallucinated citations → resolve URLs; quote-match spot checks
- Provider changes → abstraction layers and health checks
- Cost overruns → ceilings; pre-run estimates

---

## 15) Validation and evaluation

Harness:
- 10 fixed topics (technical, policy, biomedical mix)
- Metrics: time, tokens, sources count, domain diversity, dead-link rate, claim coverage, duplication
- Weekly regression run; alarms on threshold drops

Acceptance criteria:
- MVP: ≥5 reputable sources; zero orphan claims on sample topics; <6 min end-to-end on standard query
- Stage 3: repeatability (variance only on changed sources), 5 concurrent runs without timeouts
- Stage 4: UX <2 min to run/export; ≥90% non-obvious claims have ≥1 source; ≥60% have ≥2

---

## 16) Repository structure (planned)

- docs/
  - prd.md
  - master-plan.md
- src/ (MVP single-file acceptable; Stage 2+ package)
  - app.py (Streamlit UI shell)
  - agent/
    - planner.py
    - searcher.py
    - reader.py
    - analyst.py
    - verifier.py
    - writer.py
  - tools/
    - web_search.py
    - fetch_url.py
    - parse_pdf.py
  - providers/
    - cerebras_client.py
    - search_providers.py
  - storage/
    - cache.py (SQLite)
    - models.py (Pydantic v2 in Stage 2)
  - api/
    - service.py (/run endpoint; Stage 3)
- eval/
  - harness.py
  - topics.json
- exports/
- tests/
- .env.example
- requirements.txt

---

## 17) Configuration and environments

- Environment variables (.env):
  - CEREBRAS_API_KEY
  - CEREBRAS_BASE_URL=https://api.cerebras.ai/v1
  - MODEL=gpt-oss-120b
  - SEARCH_PROVIDER=duckduckgo (default)
  - MAX_ROUNDS=3
  - PER_DOMAIN_CAP=3
  - FETCH_TIMEOUT_S=15
  - ENABLE_CACHE=true (Stage 2+)
- Profiles:
  - local-dev (MVP)
  - staging (Stage 3)
  - production (Stage 4)

---

## 18) Coding standards and patterns

- Pure functions for deterministic transforms
- Typed signatures; Pydantic v2 models in Stage 2+
- Robust I/O: retries with exponential backoff, circuit breakers
- Caching-first reads; normalized URL keys; content hashing
- Claim coverage strictly enforced before finalization

---

## 19) Delivery plan and milestones

Weeks 1–2 (Stage 1 — MVP)
- Wire Cerebras client (OpenAI-compatible config)
- Implement tools: web_search, fetch_url, parse_pdf
- Implement agent loop v1 (sync I/O)
- Streamlit UI (topic input, status log, Markdown output, download .md)
- Simple claim coverage check (no orphan claims)
- Logs: tool calls, pages fetched, tokens
Deliverable: working MVP, acceptance criteria met

Weeks 3–4 (Stage 2 — Core robustness)
- Async httpx with per-domain rate limits
- Dedupe (URL normalization + SimHash/MinHash)
- Quality gate (allow/deny lists, language, length)
- SQLite caching for fetched pages and traces
- Pydantic v2 schemas; typed JSON export
- Eval harness with 10 topics + metrics
Deliverable: robustness acceptance criteria met

Weeks 5–6 (Stage 3 — Scale and control)
- Orchestrate with LangGraph
- Project workspaces, source controls in UI
- API endpoint /run with key auth
- Observability: structured traces, OTEL export
- Attachments (user PDFs/URLs)
Deliverable: throughput, repeatability, API docs

Weeks 7–8 (Stage 4 — Product polish)
- Next.js app with evidence map, exports
- Performance passes (parallelism, caching, streaming)
- Safety features (robots.txt, caps)
- Admin + usage dashboard
Deliverable: “fastest deep research” UX and coverage targets

---

## 20) Initial backlog (prioritized)

Must (MVP)
- Cerebras client setup and config
- web_search with DuckDuckGo (or Tavily if available)
- fetch_url + HTML main content extraction; parse_pdf
- Agent loop v1 with claim coverage enforcement
- Streamlit UI with logs and Markdown output
- .env.example and requirements.txt
- Minimal evaluation run on 3 sample topics

Should (Stage 2)
- Async I/O, dedupe, quality gate, caching, schemas, harness

Could (Stage 3–4)
- LangGraph orchestration, API, telemetry, attachments, Next.js UI, evidence map, exports, admin

---

## 21) Open questions

- Preferred search provider for MVP (DuckDuckGo vs Tavily availability)?
- Confirm initial 10-topic evaluation set
- Default caps for rounds, per-domain, and timeouts

---

## 22) Approval gates

- Gate A (end Week 2): MVP acceptance criteria
- Gate B (end Week 4): robustness metrics thresholds
- Gate C (end Week 6): API, repeatability, concurrency
- Gate D (end Week 8): UX, coverage, performance targets

---

## 23) Artifacts to create at project root

- requirements.txt (MVP)
- .env.example
- src/ package scaffold (even if single-file initially)
- eval/topics.json (placeholder with 10 items)
- exports/ (gitignored if necessary)
