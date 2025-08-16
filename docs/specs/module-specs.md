# Module-Level Specifications — Deep Research Agent

2025-08-15 20:21:00 - Derived from PRD and master-plan to guide implementation.

This document defines the component responsibilities, I/O contracts, invariants, error handling, performance targets, and integration notes for the MVP through Stage 3. It is implementation-agnostic and focuses on stable contracts to enable parallel work.

References:
- PRD: [../prd.md](../prd.md)
- Master Plan: [../master-plan.md](../master-plan.md)
- Memory Bank: [../../memory-bank/productContext.md](../../memory-bank/productContext.md)

---

## 1) Agent loop overview

Lifecycle (MVP):
1) Planner → 2) Searcher → 3) Reader → 4) Analyst → 5) Verifier → 6) Writer

State object passed across steps:
- topic: string
- constraints: { date_range?, include_domains[], exclude_domains[], max_rounds, per_domain_cap, timeouts }
- queries: string[]
- search_results: SearchResult[]
- documents: Document[]
- chunks: Chunk[]
- claims: Claim[]
- citations: Citation[]
- draft_sections: string[]
- final_report: { report_md, references[] }
- metrics: { duration_s, tokens_in, tokens_out, cost_est, sources_count, domain_diversity, cache_hits, cache_misses }

Termination:
- Stop when verifier reports zero orphan claims or max_rounds reached; writer produces final output with numbered citations and references.

---

## 2) Planner

Responsibility:
- Transform topic + constraints into sub-questions and initial queries that maximize credible coverage and diversity.

Inputs:
- topic: string
- constraints: { date_range?, include_domains[], exclude_domains[], max_rounds }

Outputs:
- sub_questions: string[]
- queries: string[]

Rules:
- Generate diverse query patterns (operator variants, synonyms, site/domain filters if constraints present).
- Respect include/exclude domain lists when composing queries.
- Ensure coverage across sub-questions (no single-query dominance).

Invariants:
- queries length ≥ min(3, number of sub-questions).
- All queries are deduplicated and trimmed.

Errors:
- If topic is empty → return error “INVALID_TOPIC”.

Performance:
- Latency negligible (model-assisted prompt optional); ensure generation in O(N) where N is sub-questions.

Integration notes:
- The planner may use model prompting to enrich queries. Keep prompt concise to control tokens.

---

## 3) Searcher

Responsibility:
- Call the configured search provider to return top-k SearchResult items per query, enforcing caps and normalization.

Inputs:
- queries: string[]
- k: integer
- provider: enum { duckduckgo, tavily, bing, brave } (MVP default duckduckgo)
- constraints: include_domains[], exclude_domains[], per_domain_cap

Outputs:
- search_results: SearchResult[] where SearchResult = { title, url, snippet }

Rules:
- Normalize URLs (scheme, www, trailing slash) before dedupe.
- Enforce per_domain_cap across the entire set (not per-query only).
- Filter out excluded domains; prioritize included domains.

Invariants:
- All urls are absolute (http/https).
- No duplicate urls after normalization.

Errors:
- Provider failure → retry with backoff up to N times; on persistent failure return “SEARCH_PROVIDER_UNAVAILABLE”.
- Rate limit → exponential backoff obeying provider’s guidance.

Performance:
- Aim for ≤1–2s per query roundtrip on MVP; consider batching where provider allows.

Integration notes:
- Implement provider abstraction for easy swap; default requires no API key (duckduckgo) unless Tavily chosen.

---

## 4) Reader

Responsibility:
- Fetch pages, extract main content for HTML, parse PDF, capture metadata, and chunk into token-bounded segments.

Inputs:
- urls: string[]
- fetch_timeout_s: integer
- headers: user-agent string, accept-language
- robots.txt compliance: respect disallow rules

Outputs:
- documents: Document[] = { url, title, text, source_meta }
- chunks: Chunk[] = { doc_url, text, hash, tokens }

Rules:
- Use HTTP client with timeouts, retries, and circuit breakers.
- HTML extraction: main content only; strip boilerplate, nav, ads.
- PDF parsing: text extraction; preserve page breaks minimally.
- Chunking: target token size T (e.g., 800–1200) with overlap O (e.g., 50–100).

Invariants:
- Each chunk.tokens ≤ max_token_per_chunk.
- Each Document has non-empty text or is discarded with reason recorded.

Errors:
- Network failure → retry/backoff; record dead links in metrics.
- Non-HTML/PDF types → skip or fallback to text-only extraction if safe.
- Robots disallow → skip and record.

Performance:
- MVP sync I/O acceptable; Stage 2 moves to async with per-domain rate limits.

Integration notes:
- Cache: Stage 2 stores normalized text + URL + hash in SQLite; respect cache TTL/policy.

---

## 5) Analyst

Responsibility:
- Synthesize across chunks to propose claims, associate likely sources, and draft structured sections.

Inputs:
- chunks grouped by Document
- sub_questions, constraints

Outputs:
- claims: Claim[] = { id, text, type (fact/estimate/opinion), confidence (0–1) }
- citations (interim): Citation[] = { claim_id, urls[] }
- draft_sections: string[] or structured outline

Rules:
- Prefer precise, verifiable statements with URLs; flag low-confidence items.
- Promote domain diversity in sources; avoid single-source over-reliance.
- Track claim → source mapping explicitly for verification.

Invariants:
- Every non-obvious claim has ≥1 candidate source URL.
- Claims have unique ids; stable across the loop iteration.

Errors:
- If insufficient evidence → mark claim low-confidence and propose follow-up query topics.

Performance:
- Keep prompts concise; batch across chunks where feasible.

Integration notes:
- Support incremental drafting to enable early-write behavior at Stage 4.

---

## 6) Verifier

Responsibility:
- Enforce claim coverage policy; detect unsupported or weakly supported claims; propose remediation steps (additional queries or sources).

Inputs:
- claims, interim citations, documents/chunks
- policy: ≥1 source per non-obvious claim (target ≥2 for 60% Stage 4)

Outputs:
- unsupported_claims: Claim[] subset
- follow_up_queries: string[]
- updated citations where possible

Rules:
- Resolve URLs and ensure they load; reject dead links as valid support.
- Encourage diversity; if multiple sources are same domain mirror, count as one.

Invariants:
- Zero orphan claims required before Writer finalizes.
- Follow-up queries capped by remaining budget (rounds, timeouts).

Errors:
- If verification system cannot access sources (transient) → retry small N; otherwise mark as unresolved.

Performance:
- Lightweight checks in MVP; Stage 4 adds spot-check quote matches.

Integration notes:
- Verifier informs Planner/Searcher for additional rounds if budget remains.

---

## 7) Writer

Responsibility:
- Produce final Markdown with numbered citations and a References section (URLs), ensuring formatting and coverage constraints.

Inputs:
- verified claims, citations, draft_sections, topic, constraints

Outputs:
- report_md: string (800–1,200 words target)
- references: { [n]: { url, title? } } in order of appearance

Rules:
- Inline citations as [n] in-text; stable numbering across document.
- References de-duplicated; preserve canonical URLs.
- Include brief intro, structured sections, and concise conclusion with risks/numbers where relevant.

Invariants:
- All non-obvious claims referenced.
- No broken citation indices; sequential [1..N].

Errors:
- If coverage not met → refuse finalization and request remediation cycle.

Performance:
- Streaming output optional; ensure deterministic formatting.

Integration notes:
- Provide .md export; JSON report optional in MVP.

---

## 8) Cross-cutting policies

Dedupe:
- URL normalization; text-level dedupe via SimHash/MinHash in Stage 2.
- Keep at least one representative per deduped cluster; prefer higher quality domain.

Quality gate (Stage 2):
- Domain allow/deny lists; language filter; minimal content length thresholds.

Caching (Stage 2):
- SQLite tables for pages and trace events; keys by normalized URL + content hash.

Observability:
- Log structured events: tool_call, fetch_result, chunk_made, claim_made, verify_result, writer_finalized.
- Attach request_id and topic_hash to all events.

Security:
- Respect robots.txt; redact auth tokens from URLs; never store secrets in logs.

---

## 9) Error taxonomy and retries

Common error classes:
- INVALID_INPUT, SEARCH_PROVIDER_UNAVAILABLE, NETWORK_ERROR, PARSE_ERROR, ROBOTS_DISALLOWED, DEAD_LINK, TIMEOUT, RATE_LIMITED.

Retry policy (MVP defaults):
- SEARCH/NETWORK: 2–3 retries with exponential backoff (e.g., 0.5s, 1s, 2s).
- PARSE_ERROR: no retry; record.
- RATE_LIMITED: respect provider headers; backoff accordingly.

Circuit breaker:
- Per-domain failures beyond threshold → open breaker for cool-down period.

---

## 10) Performance targets

MVP:
- End-to-end ≤6 minutes for 2–3 search rounds on standard query.
- Search: ≤1–2s/query typical.
- Reader: ≤3–4s/page typical.

Stage 4:
- 60–90s typical via parallel search+fetch, warm cache, streaming writer, and early-write.

---

## 11) Contracts and examples

Entity examples (illustrative):

SearchResult:
- { title: “Title”, url: “https://example.com/path”, snippet: “Short summary ...” }

Document:
- { url: “https://example.com/a”, title: “Page Title”, text: “...” , source_meta: { domain: “example.com”, lang: “en” } }

Claim:
- { id: “c1”, text: “gpt-oss-120b delivers ~3,000 tok/s”, type: “fact”, confidence: 0.9 }

Citation:
- { claim_id: “c1”, urls: [“https://www.cerebras.ai/news/...”, “https://insidehpc.com/... ”] }

Report:
- { topic: “X”, outline: [“Intro”, “Body”, “Conclusion”], sections: [“...”], citations: [...], references: [ { n: 1, url: “...” } ] }

---

## 12) Prompts and tool-call boundaries (MVP)

Planner prompt objectives:
- Produce sub-questions and diverse queries targeting credible sources, respecting constraints.

Analyst prompt objectives:
- Synthesize across chunks, write precise claims, associate candidate URLs, flag low confidence.

Verifier prompt objectives:
- Check coverage for all non-obvious claims, propose follow-up queries if needed.

Tool definitions (conceptual):
- web_search(query, k) → SearchResult[]
- fetch_url(url, timeout) → { html/text, meta }
- parse_pdf(url_or_bytes) → { text, meta }

To satisfy implementation traceability, reference intended functions:
- Planner method: [`planner.plan()`](../../src/agent/planner.py:1)
- Searcher method: [`searcher.search()`](../../src/agent/searcher.py:1)
- Reader method: [`reader.read()`](../../src/agent/reader.py:1)
- Analyst method: [`analyst.analyze()`](../../src/agent/analyst.py:1)
- Verifier method: [`verifier.verify()`](../../src/agent/verifier.py:1)
- Writer method: [`writer.write()`](../../src/agent/writer.py:1)

Note: Filenames are the planned locations for implementation and may be created during scaffold.

---

## 13) Acceptance checks per module (MVP)

Planner:
- Produces ≥3 diverse queries, no duplicates, respects include/exclude domains.

Searcher:
- Returns normalized, deduped URLs, respects per_domain_cap.

Reader:
- Extracts non-empty main text for ≥80% of HTML pages tested; records dead links.

Analyst:
- Produces claims with candidate URLs; no claim without at least one candidate source.

Verifier:
- Detects all orphan claims in synthetic tests; proposes reasonable follow-ups.

Writer:
- Outputs valid Markdown with sequential [n] citations and correct references list.

---

## 14) Handover notes

- This spec feeds API contracts, data schemas, evaluation harness, observability/events, security checklist, ops runbook, and performance/cost documents.
- Any change to invariants must be reflected across those artifacts and the Memory Bank.
