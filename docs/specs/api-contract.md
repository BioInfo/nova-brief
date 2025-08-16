# API Contract — Deep Research Agent

2025-08-15 20:21:41 - Initial version derived from PRD and master-plan.

Scope:
- External HTTP API for research runs and retrieval
- Stable contracts to support Stage 1 (local only) and Stage 3 (service/API)
- Payload examples, headers, status codes, and error taxonomy

References:
- PRD: [../prd.md](../prd.md)
- Master Plan: [../master-plan.md](../master-plan.md)
- Module Specs: [./module-specs.md](./module-specs.md)
- Planned service entry: [`api/service.py`](../../src/api/service.py:1)

---

## 1) Endpoints

Summary:
- POST /run — Execute a research run (MVP local; Stage 3 HTTP service)
- GET /runs/:id — Retrieve a prior run (Stage 3)
- GET /health — Liveness/readiness checks (Stage 3)
- GET /metrics — Operational metrics (Stage 3–4; may require auth)

---

## 2) POST /run

Description:
- Executes the agent loop (Planner → Searcher → Reader → Analyst → Verifier → Writer).
- Returns the final Markdown brief, optional JSON summary, and key metrics.

Request:
- Method: POST
- Path: /run
- Headers:
  - Content-Type: application/json
  - X-Request-ID: optional (if client provides, used for correlation)
  - Authorization: Bearer <KEY> (Stage 3 for team mode)
- Body (JSON):
{
  "topic": "Impacts of grid-scale battery storage on renewables integration",
  "constraints": {
    "date_range": {"from": "2022-01-01", "to": "2025-08-01"},
    "include_domains": ["nature.com", "iea.org"],
    "exclude_domains": ["reddit.com"],
    "max_rounds": 3,
    "per_domain_cap": 3,
    "timeouts": {"fetch_timeout_s": 15}
  },
  "config": {
    "search_provider": "duckduckgo",
    "k": 6,
    "model": "gpt-oss-120b",
    "cerebras_base_url": "https://api.cerebras.ai/v1",
    "enable_cache": false
  }
}

Response (200 OK):
{
  "id": "run_01J3X3A9BB5Z5TY9B0WZP6ZQ1N",
  "report_md": "# Title...\\n... [1] ...\\n\\n## References\\n[1] https://example.com/...",
  "report_json": {
    "topic": "Impacts of grid-scale battery storage...",
    "sections": ["..."],
    "citations": [{"claim_id": "c1", "urls": ["https://example.com/a", "https://example.com/b"]}],
    "references": [{"n": 1, "url": "https://example.com/a"}]
  },
  "metrics": {
    "duration_s": 241.2,
    "tokens_in": 10234,
    "tokens_out": 8361,
    "cost_est": 0.98,
    "sources_count": 9,
    "domain_diversity": 7,
    "cache_hits": 0,
    "cache_misses": 12
  }
}

Status codes:
- 200 OK — Completed run
- 202 Accepted — Run queued/async (future extension)
- 400 Bad Request — Validation error (missing/invalid fields)
- 401 Unauthorized — Missing/invalid auth (Stage 3)
- 402 Payment Required — Over org caps or quota (Stage 4 admin)
- 409 Conflict — Duplicate request detected with idempotency constraints
- 422 Unprocessable Entity — Topic empty/unsupported constraints
- 429 Too Many Requests — Concurrency/backpressure limits exceeded
- 500 Internal Server Error — Unexpected error
- 503 Service Unavailable — Provider outage or circuit breaker open

Error structure:
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "topic must be a non-empty string",
    "details": {"field": "topic"}
  }
}

Idempotency:
- Recommended header: Idempotency-Key (hash of topic + normalized constraints + config)
- If a matching successful run exists and enable_cache=true, return prior result (200)

Budget controls:
- Enforce ceilings on tokens/time/rounds; return 422 with code="BUDGET_EXCEEDED" when exceeded

---

## 3) GET /runs/:id

Description:
- Retrieve results of a prior run including report, metrics, and trace (if available).

Request:
- Method: GET
- Path: /runs/:id
- Headers:
  - Accept: application/json
  - Authorization: Bearer <KEY> (Stage 3)

Response (200 OK):
{
  "id": "run_01J3X3A9BB5Z5TY9B0WZP6ZQ1N",
  "report_md": "...",
  "report_json": {...},
  "metrics": {...},
  "trace": [
    {"ts": "2025-08-15T20:00:00Z", "kind": "tool_call", "payload": {"tool": "web_search", "query": "..." }},
    {"ts": "2025-08-15T20:00:06Z", "kind": "fetch_result", "payload": {"url": "https://..." }}
  ]
}

Status codes:
- 200 OK — Found
- 404 Not Found — Unknown id
- 410 Gone — Data expired (if retention policy applied)
- 401/403 — Auth errors (Stage 3)

---

## 4) GET /health

Description:
- Liveness and readiness checks for orchestration, provider reachability, and storage status.

Response (200 OK):
{
  "status": "ok",
  "components": {
    "cerebras": "ok",
    "search_provider": "ok",
    "cache": "degraded"
  }
}

Status codes:
- 200 OK — Healthy
- 503 Service Unavailable — Not ready

---

## 5) GET /metrics

Description:
- Exposes operational metrics (Prometheus or JSON). May require auth.

Response (200 OK, JSON exemplar):
{
  "uptime_s": 86400,
  "runs_total": 152,
  "runs_in_progress": 1,
  "avg_duration_s": 215.7,
  "error_rates": {"SEARCH_PROVIDER_UNAVAILABLE": 0.02, "DEAD_LINK": 0.07},
  "provider_latency_ms": {"search_p50": 700, "fetch_p50": 1200}
}

---

## 6) Validation rules

Topic:
- Required, non-empty, ≤ 512 chars

Constraints:
- date_range.from ≤ date_range.to
- include_domains/exclude_domains are arrays of domains (no schemes)
- max_rounds in [1, 10]
- per_domain_cap in [1, 10]
- timeouts.fetch_timeout_s in [5, 60]

Config:
- search_provider ∈ {duckduckgo, tavily, bing, brave}
- k in [3, 10]
- model default "gpt-oss-120b"
- cerebras_base_url default "https://api.cerebras.ai/v1"

---

## 7) Error taxonomy

Codes (aligned with module-specs):
- INVALID_INPUT
- SEARCH_PROVIDER_UNAVAILABLE
- NETWORK_ERROR
- PARSE_ERROR
- ROBOTS_DISALLOWED
- DEAD_LINK
- TIMEOUT
- RATE_LIMITED
- BUDGET_EXCEEDED
- CONCURRENCY_LIMIT
- INTERNAL_ERROR
- PROVIDER_UNAVAILABLE

---

## 8) Security

- Authorization: Bearer tokens for Stage 3+ endpoints
- Rate limiting per API key and IP
- Redact sensitive params in logs
- CORS: locked to first-party app domains

---

## 9) Implementation notes

- Stage 1 MVP may expose only a local function boundary rather than HTTP; keep the API shapes identical for easy migration to service in Stage 3.
- Planned HTTP handler functions:
  - [`service.run()`](../../src/api/service.py:1) — handles POST /run
  - [`service.get_run()`](../../src/api/service.py:1) — handles GET /runs/:id
  - [`service.health()`](../../src/api/service.py:1) — handles GET /health
  - [`service.metrics()`](../../src/api/service.py:1) — handles GET /metrics

Any change to this contract requires updating [./module-specs.md](./module-specs.md) and references in the Memory Bank.