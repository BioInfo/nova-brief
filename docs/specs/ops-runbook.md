# Ops Runbook — Deep Research Agent

2025-08-15 20:25:22 - Initial version. Operational guidance for running, monitoring, and troubleshooting the system across stages.

References:
- PRD: [../prd.md](../prd.md)
- Master Plan: [../master-plan.md](../master-plan.md)
- API Contract: [./api-contract.md](./api-contract.md)
- Observability: [./observability-logging.md](./observability-logging.md)
- Security: [./security-compliance.md](./security-compliance.md)
- Evaluation: [./evaluation-harness.md](./evaluation-harness.md)

---

## 1) Environments and configuration

Environment variables (.env)
- CEREBRAS_API_KEY=... (required)
- CEREBRAS_BASE_URL=https://api.cerebras.ai/v1 (default)
- MODEL=gpt-oss-120b (default)
- SEARCH_PROVIDER=duckduckgo (or tavily/bing/brave)
- MAX_ROUNDS=3
- PER_DOMAIN_CAP=3
- FETCH_TIMEOUT_S=15
- ENABLE_CACHE=false (MVP), true in Stage 2+
- LOG_LEVEL=INFO
- USER_AGENT=NovaBrief-Research/0.1
- OTEL_EXPORTER=none (MVP), otlp (Stage 3)
- RATE_LIMIT_CONCURRENCY=5 (Stage 3)
- RUN_QUEUE_LIMIT=10 (Stage 3)

Config policy
- All envs loaded at process start. Values validated; invalid aborts boot with clear error.
- Document non-defaults in release notes.

---

## 2) Health checks

Local (MVP)
- Internal function: [`service.health()`](../../src/api/service.py:1) returns status of Cerebras reachability, search provider DNS resolve, and cache path (if enabled).

Stage 3 HTTP
- GET /health:
  - status: ok | degraded | fail
  - components: cerebras, search_provider, cache
- Failure examples:
  - cerebras:fail → API not reachable or 401/403 (invalid key)
  - cache:degraded → SQLite locked or missing migrations

---

## 3) Rate limits and backpressure

Concurrency caps
- Global concurrent runs ≤ RATE_LIMIT_CONCURRENCY.
- If exceeded, respond 429 with code="CONCURRENCY_LIMIT".

Run queue (Stage 3)
- FIFO with RUN_QUEUE_LIMIT.
- When full: 429; advise retry-after seconds.

Per-domain caps (fetch)
- PER_DOMAIN_CAP requests per domain per run.
- Cooldown triggered by repeated 4xx/5xx.

Circuit breakers
- Open after N consecutive failures for a domain (e.g., N=3 for 2 minutes).
- Emit WARN event; skip domain while open.

---

## 4) Caching (Stage 2+)

SQLite path
- File: ./data/cache.sqlite
- Tables: pages, traces, runs (see [./data-schemas.md](./data-schemas.md))
- Vacuum/Prune:
  - Nightly job to remove entries older than RETENTION_DAYS (default 14)

Warm start
- Pre-warm by running common queries/topics (see evaluation harness)
- Monitor warm_improvement metric

---

## 5) Deploy and run

MVP local
- Requirements install
- .env present
- Start Streamlit UI or local runner

Stage 3 service
- WSGI/ASGI app with /run, /runs/:id, /health, /metrics
- Reverse proxy with TLS termination and rate limiting

Logging
- JSON lines to stdout; rotate by process manager or container runtime
- OTEL exporter optional

---

## 6) Incident response playbooks

A) Cerebras provider outage
- Symptoms: 503 PROVIDER_UNAVAILABLE; auth 401/403
- Checks:
  - Verify CEREBRAS_API_KEY present/valid
  - Test curl to CEREBRAS_BASE_URL
- Mitigation:
  - Exponential backoff; temporary disable new runs (429)
  - Communicate status via status banner
- Post-incident:
  - Record in [../../memory-bank/decisionLog.md](../../memory-bank/decisionLog.md)

B) Search provider failures
- Symptoms: SEARCH_PROVIDER_UNAVAILABLE; high error rates
- Checks: DNS resolve, API quota (if Tavily)
- Mitigation: fallback to duckduckgo; reduce k
- Observability: track provider_latency_ms and error_rates

C) Elevated dead links
- Symptoms: dead_link_rate > thresholds
- Checks: robots blocks, domain blocks, timeouts
- Mitigation: increase timeout temporarily; switch domains; add allowlist
- Stage 2: increase cache reliance

D) SQLite lock/contention (Stage 2+)
- Symptoms: cache:degraded, write timeouts
- Checks: open connections count; long transactions
- Mitigation: retry; serialize writes; VACUUM; shard file per env
- Long-term: move to server DB if needed

E) Cost spike
- Symptoms: cost_est deviation; runs blocked by ceilings
- Checks: token metrics, rounds increased
- Mitigation: lower MAX_ROUNDS; enforce stricter caps; pre-run estimate prompt
- Report summary in weekly review

---

## 7) Runbooks for maintenance

Weekly
- Review evaluation harness results (summary.json)
- Update dependency patch versions; check CVEs
- Prune cache per retention policy

Monthly
- Rotate keys; validate OTEL exporter endpoints
- Review domain allow/deny lists

---

## 8) SLOs and alerts

SLOs
- Availability: 99.5% for /run (Stage 3)
- Latency: P50 210s MVP; P50 75s Stage 4
- Error budget: 0.5% failed runs per week

Alerts (examples)
- High 5xx rate (>2% 5m)
- dead_link_rate above threshold
- claim_coverage < 1.0 (MVP) on tracked topics
- cache_misses spike vs baseline

---

## 9) Change management

- All config changes recorded in release notes
- Breaking changes require API contract update and Memory Bank entry
- Emergency changes post-mortem within 48h

---

## 10) Checklists

Pre-release
- [ ] Health endpoints pass
- [ ] Evaluation harness passes thresholds
- [ ] Secrets set in target environment
- [ ] Logs and traces visible in dashboard

Oncall quick checklist
- [ ] Identify failing component via logs/traces
- [ ] Contain via caps/backpressure
- [ ] Communicate user impact
- [ ] Root cause and corrective action documented