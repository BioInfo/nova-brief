# Observability & Logging Spec — Deep Research Agent

2025-08-15 20:23:52 - Initial version. Defines structured logging, tracing events, identifiers, metrics, and OpenTelemetry mapping for Stages 1–4.

References:
- PRD: [../prd.md](../prd.md)
- Master Plan: [../master-plan.md](../master-plan.md)
- Module Specs: [./module-specs.md](./module-specs.md)
- Data Schemas: [./data-schemas.md](./data-schemas.md)
- API Contract: [./api-contract.md](./api-contract.md)
- Planned trace/event models: [`models.TraceEvent()`](../../src/storage/models.py:1)
- Planned service handlers: [`api/service.py`](../../src/api/service.py:1)

---

## 1) Goals

- Provide deterministic, structured logs for every tool call and agent step
- Enable request-level correlation (request_id) and run-level correlation (run_id)
- Expose metrics for evaluation harness and operations dashboards
- Support OTEL export (traces/metrics) in Stage 3+

---

## 2) Identifiers

- request_id: client-provided or generated UUID v4; attached to all logs in the request
- run_id: generated on start of a /run execution (e.g., run_01J...)
- topic_hash: stable hash of normalized topic + constraints + config
- step_id: Planner/Searcher/Reader/Analyst/Verifier/Writer step instance id
- event_id: unique id for each TraceEvent

Generation rules:
- request_id: prefer X-Request-ID header; fallback to UUID
- run_id: prefix "run_" + ULID/KSUID
- topic_hash: sha256 of canonicalized payload

---

## 3) Log format (MVP)

- Format: JSON lines
- Fields (every line):
  - ts: ISO 8601 (UTC)
  - level: "DEBUG" | "INFO" | "WARN" | "ERROR"
  - logger: component name (e.g., "searcher", "reader", "service")
  - msg: short message
  - request_id, run_id, topic_hash (if available)
  - event: optional object with event-specific fields

Example (INFO):
{
  "ts": "2025-08-15T20:00:06Z",
  "level": "INFO",
  "logger": "reader",
  "msg": "fetch_result",
  "request_id": "3f5c...",
  "run_id": "run_01J3X...",
  "topic_hash": "a1b2...",
  "event": {"url": "https://...", "status": 200, "bytes": 53211, "latency_ms": 842}
}

Redaction:
- Remove sensitive query params (tokens, session IDs)
- Truncate overly long fields; log hashes instead if needed

---

## 4) Event taxonomy (TraceEvent.kind)

Kinds:
- tool_call — invoking web_search/fetch_url/parse_pdf
- search_result — results returned from search provider
- fetch_result — HTTP fetch outcome (status, size, url)
- chunk_made — document-to-chunk segmentation
- claim_made — analyst generated a claim
- verify_result — verifier evaluation (supported/unsupported)
- writer_finalized — final report created
- error — error occurrence with code and details

Minimum fields per kind (payload keys):
- tool_call: { tool, params, provider? }
- search_result: { query, k, results_count, provider, latency_ms }
- fetch_result: { url, status, bytes, latency_ms, robots_respected: true, cached: bool }
- chunk_made: { doc_url, chunks_count, avg_tokens }
- claim_made: { claim_id, confidence, sources_count }
- verify_result: { orphan_claims, follow_up_queries_count }
- writer_finalized: { words_count, references_count, coverage: { claims: N, covered: N } }
- error: { code, message, category, retried: int }

All events include ts, request_id, run_id, topic_hash.

---

## 5) Metrics

Operational metrics:
- runs_total, runs_in_progress, runs_failed_total
- provider_latency_ms: search_p50/p95, fetch_p50/p95
- error_rates by code (e.g., DEAD_LINK, TIMEOUT, RATE_LIMITED)
- cache_hits, cache_misses (Stage 2)
- concurrency: current vs limit
- duration_s: distribution over time

Evaluation metrics (see harness):
- claim_coverage, strong_coverage
- sources_count, domain_diversity
- dead_link_rate, duplication_rate
- warm_improvement (Stage 2)

---

## 6) OpenTelemetry mapping (Stage 3)

Traces:
- Span per /run (name: "run")
  - Child spans per step: planner/searcher/reader/analyst/verifier/writer
  - Child spans per tool call: web_search/fetch_url/parse_pdf
- Span attributes:
  - request_id, run_id, topic_hash
  - provider, url, status_code (for fetch)
  - counts (results_count, chunks_count, references_count)

Logs:
- OTEL log records mirrored from structured logs; maintain same fields

Metrics:
- Export counters/gauges/histograms corresponding to section 5
- Prometheus-compatible endpoint recommended

---

## 7) Levels and sampling

Levels:
- INFO default for successful events
- DEBUG for verbose details (disabled by default in prod)
- WARN for degraded operations (e.g., cache degrades)
- ERROR for failures; include code and category

Sampling:
- Logs: full for MVP; Stage 3 production may sample DEBUG
- Traces: head-based sampling 10–20% in production; 100% for errors

---

## 8) Privacy and security in observability

- Redact tokens and sensitive parameters from URLs and payloads
- Do not store user-uploaded raw documents in logs; only hashes/metadata
- PII: avoid collecting; if present in uploaded docs, do not emit in logs/traces

---

## 9) Storage and retention

- Local dev: logs to stdout, traces to local file or SQLite (Stage 2)
- Stage 3+: forward to centralized log store (e.g., ELK) and OTEL collector
- Retention: 7–14 days for logs by default; traces 7 days; configurable

---

## 10) Error handling conventions

- Every ERROR event includes:
  - code (from taxonomy)
  - message (developer-focused)
  - category (SEARCH, NETWORK, PARSE, POLICY, SYS)
  - retried count
  - consequence (e.g., "skipped_url")

- Circuit breaker changes emit WARN with domain and cooldown

---

## 11) Implementation hooks

Planned functions:
- Logger factory: [`observability.get_logger()`](../../src/storage/models.py:1)  // placeholder reference
- Trace emit: [`observability.emit_event()`](../../src/storage/models.py:1)
- Metrics recorders:
  - [`observability.inc_counter()`](../../src/storage/models.py:1)
  - [`observability.observe_latency()`](../../src/storage/models.py:1)

Note: Actual file locations will be placed under src/observability during scaffold.

---

## 12) Change control

- Any event schema change updates this document
- Update [./data-schemas.md](./data-schemas.md) for TraceEvent if fields change
- Append rationale in Memory Bank: [../../memory-bank/decisionLog.md](../../memory-bank/decisionLog.md)