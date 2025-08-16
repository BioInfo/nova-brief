# System Patterns (Optional)

This file documents recurring patterns and standards used in the project. It is optional, but recommended to be updated as the project evolves.
2025-08-15 20:17:05 - Initialized from docs/prd.md via Initiate Memory Bank (command "i").

*

## Coding Patterns

- Tool interfaces: define consistent signatures for web_search, fetch_url, parse_pdf; return typed dicts/schemas (Stage 2+: Pydantic models)
- Robust fetching: retries with backoff and circuit breakers; respect robots.txt and per-domain caps
- Caching-first I/O: check SQLite cache before network; persist normalized text + URL + hash
- Deterministic logs: structured JSON with request IDs; redact sensitive params
- Claim coverage enforcement: maintain claim → sources map; fail verification if uncovered

## Architectural Patterns

- Agent loop composition: Planner → Searcher → Reader → Analyst → Verifier → Writer (explicit in Stage 3 via LangGraph)
- API boundary: backend /run endpoint encapsulates orchestration; UI (Streamlit/Next.js) is a thin client
- Abstraction for providers: pluggable search (DuckDuckGo/Tavily/Bing/Brave); model via OpenAI-compatible client pointing to Cerebras
- Observability: traces and metrics emitted as structured events; optional OpenTelemetry export
- Scaling path: parallel search+fetch; warm caches; concurrency controls; queue + backpressure for >N runs

## Testing Patterns

- Harness-based evaluation: 10 fixed topics; metrics for time, tokens, sources, diversity, dead-links, claim coverage, duplication
- Dead-link and duplication checks baked into CI-like runs (threshold alarms)
- Golden outputs for smoke tests; allow variance mainly in changing sources
- Spot-check citation integrity: quote-match random samples against sources