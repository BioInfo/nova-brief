# Performance & Cost Model — Deep Research Agent

2025-08-15 20:26:02 - Initial version. Establishes latency/cost models, ceilings, and tuning levers from MVP to Stage 4.

References:
- PRD: [../prd.md](../prd.md)
- Master Plan: [../master-plan.md](../master-plan.md)
- API Contract: [./api-contract.md](./api-contract.md)
- Module Specs: [./module-specs.md](./module-specs.md)
- Observability: [./observability-logging.md](./observability-logging.md)
- Evaluation: [./evaluation-harness.md](./evaluation-harness.md)

---

## 1) Latency model

End-to-end duration_s (MVP, sequential):
- duration_s ≈ T_planner + R × (T_search + K_fetch × T_fetch_avg + T_read_extract + T_analyze + T_verify) + T_write
  - R = search rounds (≤ max_rounds)
  - K_fetch = pages fetched per round (k results × selection rate)
  - T_fetch_avg ≈ mean HTTP latency + extraction
- Target (MVP): ≤ 360s median for R ∈ {2,3}
- Stage 4 (parallelism + caching + streaming): 60–90s typical

Component budgets (MVP guidance):
- Search per query: 0.7–2.0s
- Fetch per page: 1.0–3.0s HTML, 2.0–6.0s PDF
- Analyze/Verify per round: 5–30s depending on tokens
- Writer: 10–25s (depends on output tokens; streaming reduces wall time to first content)

Parallelism plan:
- Stage 2: async fetch (httpx.AsyncClient), per-domain rate limits, batch search (provider-dependent)
- Stage 4: parallel search+fetch; early-write of draft while reading continues

---

## 2) Token and cost model

Definition:
- tokens_in: sum of prompt tokens across planner/analyst/verifier/writer/tool-calling
- tokens_out: sum of generated tokens (writer + intermediate model outputs)
- cost_est = unit_price_in × tokens_in + unit_price_out × tokens_out
  - For Cerebras GPT-OSS-120B pay-as-you-go, use published rates (see provider); replace placeholders upon availability.

Estimation (MVP conservative):
- Planner: 0.5–1.5k in, 0.2–0.8k out per run
- Analyst (per round): 1.5–3k in, 0.6–1.5k out
- Verifier (per round): 0.5–1.5k in, 0.2–0.6k out
- Writer: 1–1.5k in, 0.8–1.2k out (target 800–1,200 words)

Budget ceilings (API enforceable):
- MAX_TOKENS_IN: 30k (MVP default)
- MAX_TOKENS_OUT: 20k (MVP default)
- MAX_COST_USD: 2.00 per run (configurable)
- MAX_DURATION_S: 360 (MVP); 120 (Stage 4)

When exceeded:
- Return 422 BUDGET_EXCEEDED with partial metrics and guidance
- Provide recommendations (reduce rounds, k, enable cache)

---

## 3) Configuration levers

Throughput vs quality:
- rounds (R): fewer rounds reduce latency/cost; risk lower coverage
- k (search top-k): lower k reduces fetches; risk missing sources
- per_domain_cap: reduces duplicates; improves diversity
- fetch_timeout_s: lower reduces latency; risk higher dead_link_rate
- chunk size tokens: larger chunks reduce LLM calls; risk lower precision
- model parameters: temperature/penalties to stabilize outputs

Caching (Stage 2):
- enable_cache: true — reduces fetch and analyze cost on warm runs
- TTL/policy: prefer content-hash based; detect staleness by age or ETag/Last-Modified if available

---

## 4) Tuning procedure

MVP weekly tuning:
1) Run evaluation harness (cold)
2) Record latency and cost metrics
3) Adjust R, k, fetch_timeout_s to hit latency ≤ 360s with coverage targets
4) Validate dead_link_rate < 0.10

Stage 2 tuning:
1) Enable cache; establish warm baseline
2) Tune per-domain rate limits and concurrency to reduce tail latency
3) Introduce dedupe and quality gate to reduce wasted fetch/analysis
4) track warm_improvement ≥ 0.20

Stage 4 tuning:
- Early-write activation, aggressive parallelism, prefetch likely sources, streaming writer

---

## 5) Example pre-run estimate

Given:
- R=2, k=6, selection rate=0.7 ⇒ K_fetch ≈ 8 pages
- T_fetch_avg=2.0s, T_search=1.0s, T_read_extract=4.0s, T_analyze=12s, T_verify=6s, T_planner=3s, T_write=18s

Estimate:
- duration_s ≈ 3 + 2 × (1 + 8×2 + 4 + 12 + 6) + 18
- = 3 + 2 × (1 + 16 + 4 + 12 + 6) + 18
- = 3 + 2 × 39 + 18
- = 99s (approx; conservative buffers can double to 180–220s)

Token estimate:
- tokens_in ≈ 10k; tokens_out ≈ 8k
- cost_est = unit_price_in×10k + unit_price_out×8k

---

## 6) Guardrails

- Hard ceilings enforced in code for tokens, rounds, and duration
- Circuit breakers prevent repeated domain fetching failures
- Idempotency and cache reuse to avoid accidental reruns
- Clear user feedback on which limit triggered and how to adjust

---

## 7) KPIs to track

- duration_s P50/P95; tokens_in/out averages
- cost_est mean/95th
- sources_count, domain_diversity
- dead_link_rate, duplication_rate
- cache_hits/misses; warm_improvement
- error_rates by category

---

## 8) Change control

Any changes to ceilings or formulas:
- Update this document
- Update API validation/rules
- Log decision in Memory Bank: [../../memory-bank/decisionLog.md](../../memory-bank/decisionLog.md)