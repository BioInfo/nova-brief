# Product Context

This file provides a high-level overview of the project and the expected product that will be created. It is initialized from the current documentation in docs/ (including docs/prd.md and docs/master-plan.md). This file is intended to be updated as the project evolves, and should be used to inform all other modes of the project's goals and context.
2025-08-16 15:36:55 - Initialized from docs/prd.md and docs/master-plan.md

*

## Project Goal

Build a fast, reliable deep-research agent that plans, searches, reads, verifies, and writes analyst-grade, cited briefs (800–1,200 words). Ship a Python MVP with Streamlit, then scale to a robust, observable, and performant product. The system now uses OpenRouter’s OpenAI-compatible API, pinned to the Cerebras provider running model "openai/gpt-oss-120b", with a roadmap toward structured JSON outputs via JSON Schema.

## Key Features

- End-to-end agent loop: Planner → Searcher → Reader → Analyst → Verifier → Writer
- Tooling: web search, URL fetch and extract (HTML/PDF), dedupe, quality gate, citation validation
- Strict citation policy: all non-obvious claims must be backed by ≥1 source (target ≥2 for 60%+ by Stage 4)
- Outputs: Markdown brief with numbered citations and References section; JSON export (Stage 2+)
- Performance/Cost visibility: token counts, timings, source counts; guardrails and ceilings
- Configurability: date ranges, domain allow/deny lists, per-domain caps, timeouts
- Robustness: retries, backoff, circuit breakers; SQLite cache (Stage 2+)
- Observability (Stage 3+): structured traces, OpenTelemetry export
- Product polish (Stage 4): Next.js UI, evidence map, exports, admin/usage dashboards

## Overall Architecture

- Runtime (MVP → Scale): Client UI (Streamlit) → Backend service (/run) → Agent loop (Planner→Searcher→Reader→Analyst→Verifier→Writer) → OpenRouter API (/chat/completions) + search/fetch tools → SQLite cache (Stage 2+) → Storage (reports)
- Model provider: OpenAI-compatible client pointing at OpenRouter
  - base_url: https://openrouter.ai/api/v1
  - api_key: OPENROUTER_API_KEY
  - model: "openai/gpt-oss-120b"
  - routing: providers=["cerebras"] to pin to Cerebras
- Data model progression: Stage 1 typed dicts → Stage 2 Pydantic v2 models + typed JSON export
- Structured output: Writer to supply JSON Schema (derived from Pydantic Report) to enforce valid JSON via OpenRouter’s structured output/tool-calling
- API (Stage 3): /run, /runs/:id; health and metrics endpoints; key-based auth
- Performance strategy: parallel search/fetch, caching, streaming writer, early-write behavior
- Operations: env-configured caps, concurrency/backpressure, health checks, incident playbooks

## Staged Delivery (Milestones)

- Stage 1 (Weeks 1–2): MVP with OpenRouter client pinned to Cerebras; web_search/fetch_url/parse_pdf; agent loop v1; Streamlit UI; basic claim coverage; logs
- Stage 2 (Weeks 3–4): Async httpx with per-domain rate limits; dedupe; quality gate; SQLite cache; Pydantic v2 schemas; evaluation harness with 10 topics
- Stage 3 (Weeks 5–6): Orchestration with LangGraph; workspaces; /run API with key auth; observability with traces/OTEL; attachments
- Stage 4 (Weeks 7–8): Next.js app; evidence map; further performance passes; safety (robots.txt, caps); admin + usage dashboard

## Configuration (MVP defaults)

- OPENROUTER_API_KEY
- OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
- MODEL="openai/gpt-oss-120b"
- SEARCH_PROVIDER=duckduckgo
- MAX_ROUNDS=3
- PER_DOMAIN_CAP=3
- FETCH_TIMEOUT_S=15
- ENABLE_CACHE=false (MVP), true in Stage 2+

## Risks & Mitigations (Highlights)

- Paywalls/anti-bot → summaries, public alternates, user PDFs
- Source spam → quality scores + allow/deny lists
- Hallucinated citations → URL resolution checks; spot-check quotes
- Provider issues → health checks; incident playbooks (OpenRouter/Cerebras); retry/backoff; queue caps
- Cost overruns → ceilings; pre-run estimates

---

2025-08-16 15:36:55 - Initialized Product Context from docs/prd.md and docs/master-plan.md with OpenRouter + Cerebras provider pinning, model "openai/gpt-oss-120b", and structured JSON output plan.