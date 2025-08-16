# Evaluation Harness — Deep Research Agent

2025-08-15 20:23:25 - Initial version. Defines topics, metrics, formulas, thresholds, and the run protocol for consistent evaluation across stages.

References:
- PRD: [../prd.md](../prd.md)
- Master Plan: [../master-plan.md](../master-plan.md)
- Data Schemas: [./data-schemas.md](./data-schemas.md)
- API Contract: [./api-contract.md](./api-contract.md)
- Planned harness runner: [`eval/harness.py`](../../eval/harness.py:1)

---

## 1) Objectives

- Quantify quality and reliability of outputs (coverage, sources, diversity).
- Track latency and cost across iterations.
- Detect regressions via weekly runs and thresholds with alarms.

---

## 2) Topics set (v0)

A balanced, 10-item fixed set. Each item includes a short description and any constraints.

1. Grid-scale battery storage and renewables integration
   - Focus: integration benefits, costs, intermittency mitigation
   - Constraints: 2022-01-01 to present; prefer academic/industry sources
2. Semiconductor packaging advances (2.5D/3D, chiplets)
   - Focus: yield, cost, performance trade-offs
   - Constraints: prefer IEEE/ACM, TSMC/Intel sources
3. mRNA vaccine platform expansion beyond SARS-CoV-2
   - Focus: oncology, auto-immune, manufacturing scale-up
   - Constraints: peer-reviewed emphasis
4. Carbon capture technologies (post-combustion vs DAC)
   - Focus: costs, energy penalty, deployment status
   - Constraints: DOE/IEA primary sources preferred
5. Quantum error correction current approaches
   - Focus: surface codes, thresholds, hardware constraints
   - Constraints: arXiv, Nature, Google/IBM papers
6. AI code generation impact on software productivity
   - Focus: empirical results, risks, limitations
   - Constraints: industry reports + peer review
7. Microplastics impacts on human health
   - Focus: exposure pathways, quantified risks
   - Constraints: medical journals priority
8. Fusion energy commercialization timelines
   - Focus: tokamak vs stellarator vs ICF, milestones
   - Constraints: government labs and operator updates
9. LEO satellite internet economics
   - Focus: CAPEX/OPEX, ARPU, coverage, constraints
   - Constraints: filings, operator reports, credible analysts
10. Cerebras GPT-OSS-120B performance and use cases
    - Focus: throughput (~3,000 tok/s), workloads, trade-offs
    - Constraints: vendor posts + third-party validation

Stage 2+: rotate-in variants but retain a stable core of 10 for comparability.

---

## 3) Metrics and formulas

Latency:
- duration_s: wall-clock seconds from request start to final report
- Formula: end_ts - start_ts per run

Tokens and cost:
- tokens_in, tokens_out: model token counters or approximations
- cost_est: provider unit pricing × (tokens_in + tokens_out)

Source quality:
- sources_count: number of unique resolved URLs in references
- domain_diversity: number of unique eTLD+1 across references
- dead_link_rate: dead_links / total_links_fetched
  - dead_links: HTTP errors (4xx/5xx), timeouts, or robots disallow

Coverage:
- claim_coverage: fraction of non-obvious claims with ≥1 source
- strong_coverage: fraction with ≥2 sources
- orphan_claims: count where citations list is empty

Duplication:
- duplication_rate: size(near-duplicate clusters) / total_documents
  - Use SimHash/MinHash in Stage 2; MVP approximates via URL + title

Reliability:
- error_rates by category (SEARCH_PROVIDER_UNAVAILABLE, DEAD_LINK, TIMEOUT, etc.)

Caching benefit (Stage 2):
- warm_improvement: (cold_duration_s - warm_duration_s) / cold_duration_s

---

## 4) Thresholds and acceptance criteria

MVP (Stage 1) acceptance:
- ≥5 reputable sources per typical brief
- claim_coverage = 1.0 (zero orphan_claims) on topics 1, 2, 4, 10
- duration_s ≤ 360 seconds (6 minutes) on median
- dead_link_rate < 0.10

Stage 2 acceptance:
- dead_link_rate < 0.05
- duplication_rate < 0.10
- warm_improvement ≥ 0.20 (20% faster with cache)
- domain_diversity median ≥ 6 on set

Stage 3 acceptance:
- Repeatability: two runs of same topic/config differ only due to changed sources; variance bounds documented
- Concurrency: 5 concurrent runs complete without timeouts (P95 duration within 1.5× single-run P50)

Stage 4 acceptance:
- UX: new user can run and export in <120 seconds typical
- Coverage: claim_coverage ≥ 0.90; strong_coverage ≥ 0.60
- Post-run report shows sources, costs, and time saved

---

## 5) Run protocol

Per topic:
1) Generate a deterministic request payload (seeded if applicable).
2) Execute /run or local function equivalent.
3) Persist outputs: report_md, report_json (if available), metrics, trace (if available).
4) Compute metrics using standardized utilities.
5) Append results to a CSV/JSON summary.

Cold vs warm:
- Cold run: empty cache
- Warm run: repeat with cache enabled
- Compare durations and cache hit/miss metrics

Concurrency test (Stage 3):
- Execute 5 topics simultaneously; record success, latency, and error categories.

---

## 6) Data capture

Files (per run):
- eval/results/{run_id}/report.md
- eval/results/{run_id}/report.json
- eval/results/{run_id}/metrics.json
- eval/results/{run_id}/trace.json (if enabled)

Aggregate:
- eval/results/summary.csv
- eval/results/summary.json

---

## 7) Reporting

Weekly regression:
- Compute medians and P95 for duration_s and tokens
- Report coverage, strong_coverage, domain_diversity medians
- Track error_rates by category
- Highlight deltas > ±10% vs previous week

Alarms:
- If dead_link_rate > 0.10 (MVP) or > 0.05 (Stage 2), flag
- If claim_coverage < 1.0 (MVP) on covered topics, flag
- If duplication_rate > 0.10 (Stage 2), flag

---

## 8) Implementation notes

- Runner location: [`eval/harness.py`](../../eval/harness.py:1)
- Topics list: eval/topics.json (seeded with the 10 topics above)
- Metric utilities:
  - tokenize approximation
  - URL normalization and eTLD+1 extraction
  - dead link detection
  - duplicate clustering (Stage 2)

---

## 9) Change control

Any edits to topics or thresholds:
- Update this file
- Update eval/topics.json
- Log in Memory Bank: [../../memory-bank/decisionLog.md](../../memory-bank/decisionLog.md) with timestamp and rationale