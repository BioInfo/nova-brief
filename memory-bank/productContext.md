# Product Context

This file provides a high-level overview of the project and the expected product that will be created. Initially it is based upon docs/prd.md and all other available project-related information in the working directory. This file is intended to be updated as the project evolves, and should be used to inform all other modes of the project's goals and context.
2025-08-15 20:15:38 - Initialized from docs/prd.md (PRD: Deep Research Agent) via Initiate Memory Bank (command "i").

*

## Project Goal

Build a fast, reliable deep-research agent that plans, searches, reads, verifies, and writes analyst-grade, cited briefs (800–1,200 words) using Cerebras GPT-OSS-120B through an OpenAI-compatible API. Deliver a Python MVP with a simple UI (Streamlit), then iterate through robustness, orchestration/APIs, and a polished web app with high throughput on Cerebras.

## Key Features

- End-to-end agent loop: Planner → Searcher → Reader → Analyst → Verifier → Writer
- Tooling: web search, URL fetch and extract (HTML/PDF), dedupe, quality gate, citation validator
- Strict citation policy: all non-obvious claims must be backed by at least one source
- Output: Markdown brief with numbered citations and “References” section
- Speed and cost visibility: token counts and spend per run; throughput optimized via Cerebras
- Configurable constraints: date ranges, domain allow/deny lists, per-domain caps, timeouts
- Caching and robustness: retries, backoff, circuit breakers; SQLite cache (Stage 2+)
- Orchestration and observability (Stage 3+): LangGraph, structured traces, OpenTelemetry
- Polished UX (Stage 4): Next.js UI, live traces, evidence map, inline citation previews, exports

## Overall Architecture

- Runtime (MVP → Scale): Client UI → Backend service (/run) → Agent loop → Cerebras chat API (OpenAI-compatible) + search/fetch tools → SQLite cache → Storage (reports)
- Model: gpt-oss-120b on Cerebras Inference Cloud (OpenAI-compatible endpoints)
- Key components: 
  - Planner: break topic into sub-questions; propose queries
  - Searcher: call search API; return top-k results
  - Reader: fetch and extract text; split to chunks
  - Analyst: synthesize; track claim-to-source links
  - Verifier: find unsupported claims; trigger follow-ups
  - Writer: produce final Markdown with references
- Data model (Stage 2+ with Pydantic v2): SearchResult, Document, Chunk, Claim, Citation, Report, TraceEvent, Config

## Users and Jobs-to-be-Done

- Analysts / PMs: fast first-pass research with credible sources
- Engineers / Scientists: technical overviews with links to primary papers
- Executives: single-screen brief with risks, numbers, sources

## Functional and Non-Functional Requirements (Summary)

- Input: topic + optional constraints
- Output: cited Markdown brief + references, plus JSON exports (later)
- Tool-calling: web_search, fetch_url, parse_pdf
- Verification: reject non-obvious claims lacking sources
- Limits: max search rounds, per-domain caps, request timeouts
- Latency: MVP ≤6 min; Stage 4 target 60–90 sec
- Reliability: deterministic retries/backoff; robust fetch pipeline
- Cost: show token usage and spend per run; guardrails/ceilings

## Staged Delivery Plan (Milestones)

- Stage 1 (MVP): Python 3.11 + Streamlit, Cerebras via OpenAI client, basic tools (httpx, trafilatura, pypdf), in-memory data, simple claim coverage, logs; acceptance: ≥5 reputable sources, 0 orphan claims, <6 min E2E
- Stage 2 (Robustness): async httpx, dedupe (URL normalization + SimHash/MinHash), quality gates, SQLite caching, Pydantic v2 schemas, eval harness; acceptance: dead-link <5%, dupes <10%, visible cache improvements
- Stage 3 (Scale & Control): LangGraph, project workspaces, source controls (date/academic-only/caps), observability (JSON traces, OTEL), attachments, team mode (/run API with key auth); acceptance: repeatability, 5 concurrent runs, API docs
- Stage 4 (Product Polish): Next.js app with live trace/evidence map/export, speed optimizations (parallel search/fetch, aggressive caching, 3,000 tok/s streaming), safety (robots.txt, request caps), integrations (Tavily/Bing/Brave), admin & usage dashboard; acceptance: UX <2 min to run/export, ≥90% claim coverage (≥1 source), ≥60% (≥2 sources)

## APIs (Planned)

- POST /run: input {topic, constraints?, config?}; returns {report_md, report_json, metrics}
- GET /runs/:id: returns prior result + trace

## Evaluation

- Harness of 10 fixed topics with metrics: time, tokens, sources, diversity, dead-links, claim coverage, duplication
- Optional comparisons with open deep-research frameworks

## Security & Compliance

- Respect robots.txt and site terms; avoid storing raw pages unless cached; store extracted text + URL + hash
- Secrets hygiene; PII avoidance; encrypted storage for uploads; redact sensitive URL params in logs

## Risks & Mitigations (Highlights)

- Paywalls/anti-bot → public alternates, user PDFs
- Source spam → quality scores + allow/deny lists
- Hallucinated citations → URL resolution checks; quote-match spot checks
- Provider changes → abstraction for search; health checks
- Cost overruns → ceilings; pre-run cost estimates

---

(Notes) Pydantic v2 is optional for MVP; becomes valuable for Stage 2+ for schemas, validation, and stable JSON exports.
