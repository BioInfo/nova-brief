# Security & Compliance Checklist — Deep Research Agent

2025-08-15 20:24:32 - Initial version aligned with PRD, master-plan, and observability spec. This checklist establishes policy and practical controls for MVP through Stage 4.

References:
- PRD: [../prd.md](../prd.md)
- Master Plan: [../master-plan.md](../master-plan.md)
- Observability: [./observability-logging.md](./observability-logging.md)
- API Contract: [./api-contract.md](./api-contract.md)
- Data Schemas: [./data-schemas.md](./data-schemas.md)

---

## 1) Web compliance (robots.txt and site terms)

- Robots adherence:
  - Respect Disallow rules for the effective user-agent.
  - Set a distinct user-agent string for the app (e.g., "NovaBrief-Research/0.1").
  - Per-site request caps; implement cooldown and circuit breaker on repeated errors.
- Rate limits:
  - Enforce per-domain concurrency and minimum gaps (Stage 2).
- Legal:
  - Honor site terms; do not bypass paywalls or anti-bot protections.
- Logging:
  - Record robots decisions (allowed/blocked) in events as part of fetch_result.

---

## 2) Secrets management

- No keys in code or repo.
- Use environment variables for:
  - CEREBRAS_API_KEY
  - Optional: search provider keys (e.g., Tavily)
- .env.example contains placeholders only; never actual keys.
- Rotation:
  - Keys rotatable without redeploy; document procedure in ops runbook.
- Access control:
  - Stage 3 API requires Bearer tokens; server-side key storage isolated from logs.

---

## 3) PII and data handling

- Avoid collecting PII.
- If user uploads documents at later stages:
  - Encrypt at rest (AES-256 or provider standard).
  - Do not log document contents; only hashes and metadata.
  - Provide deletion endpoint/policy for user-supplied artifacts.
- Redaction:
  - Strip/obfuscate auth tokens and signed query params from URLs in logs and traces.

---

## 4) Storage and retention

- MVP:
  - Do not persist raw pages beyond ephemeral memory (unless caching is enabled).
- Stage 2 caching (SQLite):
  - Store extracted text + URL + hash, not full raw HTML/PDF where practical.
  - Retention policy: 7–30 days configurable; scheduled cleanup task.
- Traces/logs retention:
  - Local dev: developer-controlled.
  - Stage 3+: central log store with 7–14 day retention unless regulated.

---

## 5) Access and authorization (Stage 3+)

- API:
  - Bearer token auth; per-key rate limits.
  - Optional roles: viewer, runner, admin (lightweight policy).
- CORS:
  - Only allow first-party UI origins.
- Audit:
  - Log auth principal on requests (redacted where necessary).

---

## 6) Network and request hygiene

- TLS-only endpoints for external services.
- Timeouts and retries:
  - Avoid indefinite hangs; enforce caps aligned with API contract.
- Header policies:
  - Standardize user-agent, accept-language; avoid leaking environment info.

---

## 7) Observability and incident response

- All ERROR logs include code, category, retried count, and consequence.
- Alarms:
  - Dead-link rate thresholds, claim coverage regressions, error-rate spikes.
- Incident playbook:
  - Identify failing component (provider, fetch, parser, model).
  - Mitigation steps (fallback provider, backoff tuning, cache warmup).
  - Post-incident: record in Decision Log and Ops Runbook.

---

## 8) Compliance posture

- Content usage:
  - Use fair-use summaries and public sources; do not store paywalled content beyond policy.
- Data residency:
  - No residency requirement initially; document if requirements change.
- Privacy notices:
  - UI to display a brief privacy note and link to policy (Stage 4 web app).

---

## 9) Build and supply chain

- Pin critical Python dependencies in requirements.txt.
- Verify hashes where feasible.
- Regularly update to patch CVEs; document cadence (e.g., monthly).
- Optional: adopt dependency scanning in CI (Stage 3–4).

---

## 10) Change control and documentation

- Any change to security/compliance controls:
  - Update this checklist.
  - Update observability and API docs if affected.
  - Append entry in Memory Bank: [../../memory-bank/decisionLog.md](../../memory-bank/decisionLog.md) with timestamp and rationale.

---

## 11) Acceptance checks

MVP (Stage 1):
- Robots respected; no paywall bypass.
- Secrets only via env vars; .env.example provided.
- Logs redact tokens/PII; no raw content stored beyond runtime.

Stage 2:
- Caching stores extracted text + URL + hash; retention policy enforced.
- Per-domain rate limits and circuit breakers in place.

Stage 3–4:
- AuthZ in API; rate limiting; OTEL export with sanitized data.
- Incident response documented; alarms configured and tested.