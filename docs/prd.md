# PRD: Deep Research Agent (Cerebras + GPT-OSS-120B)

## 1) Overview

Build a fast, reliable deep-research agent that plans, searches, reads, verifies, and writes cited briefs. Start small. Ship a usable MVP in Python with a simple UI. Scale to a beautiful, production web app with high throughput on **Cerebras** using **GPT-OSS-120B** via OpenAI-compatible APIs. ([inference-docs.cerebras.ai][1], [Cerebras][2])

**Why this stack**

* **Speed**: GPT-OSS-120B runs at \~3,000 tok/s on Cerebras Inference Cloud. Good for multi-step research loops. ([Cerebras][3], [Inside HPC & AI News][4])
* **Simple integration**: OpenAI-compatible API; swap your client with `base_url=https://openrouter.ai/api/v1` and configure it to route exclusively to the Cerebras provider. ([inference-docs.cerebras.ai][1])
* **Open ecosystem**: Compatible with open deep-research frameworks for faster iteration if needed. ([GitHub][5], [LangChain Blog][6], [FlowiseAI][7])

---

## 2) Goals and non-goals

**Goals**

* Produce analyst-grade briefs (800–1,200 words) with numbered citations and a reference list.
* Enforce claim→source coverage for all non-obvious claims.
* Minimize manual tuning; use sensible defaults.
* Keep cost observability and speed top-of-mind.

**Non-goals (for MVP)**

* No account system or multi-tenant admin.
* No heavy knowledge graph or notebook runner.
* No paidwall bypass or scraping beyond robots.txt.

---

## 3) Users and jobs-to-be-done

* **Analysts / PMs**: Fast first-pass research with credible sources.
* **Engineers / Scientists**: Technical overviews with links to primary papers.
* **Execs**: One-screen brief with risks, numbers, and sources.

---

## 4) System at a glance

**Agent loop**: Planner → Searcher → Reader → Analyst → Verifier → Writer.
**Tools**: Web search, URL fetch + extract (HTML/PDF), dedupe, quality gate, citation validator.
**Model**: `gpt-oss-120b` on Cerebras (OpenAI-compatible chat with tool calling). ([inference-docs.cerebras.ai][1], [Cerebras][2])

---

## 5) Functional requirements (all stages)

* Input: topic and optional constraints (date range, domains to include/exclude).
* Output: Markdown brief with `[n]` citations and a “References” section (URLs).
* Tool calling: model can call `web_search`, `fetch_url`, and `parse_pdf`.
* Verification pass: reject any non-obvious claim without ≥1 source.
* Limits: max search rounds, per-domain caps, request timeouts.

**Non-functional**

* **Latency targets**

  * MVP: ≤6 min end-to-end for 2–3 search rounds.
  * Stage 4: ≤60–90 sec for typical briefs (parallelism + caching).
* **Cost**: show estimated tokens and spend per run; pay-as-you-go on Cerebras. ([Cerebras][8])
* **Reliability**: deterministic retries, backoff, and circuit breakers on fetch.

---

## 6) Staged delivery plan

### Stage 1 — MVP (ship first)

**Scope**

* Python 3.11, single file or small package.
* **UI**: Streamlit (text box + “Run”).
* **Model**: OpenRouter via OpenAI client; `model="openai/gpt-oss-120b"`, with API calls configured to use the Cerebras provider only.
* **Tools**: `web_search` (DuckDuckGo or Tavily), `fetch_url` with `httpx` + `trafilatura`, `parse_pdf` with `pypdf`.
* **Data**: in-memory; optional `.md` and `.json` export (report + citations).
* **Validation**: simple claim coverage check.

**Deliverables**

* Working app: topic → cited brief.
* Config via `.env` (`OPENROUTER_API_KEY`).
* Basic logs: tool calls, pages fetched, tokens used.

**Acceptance criteria**

* ≥5 reputable sources in a typical brief.
* Zero orphan claims on sample topics.
* End-to-end <6 min on a standard query.

### Stage 2 — Core robustness

**Scope**

* Switch HTTP to **async** (`httpx.AsyncClient`) with per-domain rate limits.
* Add **dedupe** (URL normalization + text SimHash/MinHash).
* **Quality gate**: domain allow/deny lists, length thresholds, language filter.
* **Caching**: SQLite for fetched pages and traces.
* **Schemas**: introduce **Pydantic v2** for `SearchResult`, `Document`, `Claim`, `Citation`, `Report`, `TraceEvent` (typed JSON export).
* **Eval harness**: 10 canned tasks; metrics for citation coverage, dead-link rate, domain diversity, time, and tokens.

**Acceptance criteria**

* Dead-link rate <5% on harness.
* Duplicate content <10% of corpus after dedupe.
* Cold run and warm-cache improvements visible in logs.

### Stage 3 — Scale and control

**Scope**

* Orchestration with **LangGraph** (or equivalent) for explicit plan ↔ tools ↔ verify loops.
* **Project workspaces**: save runs, edit prompts, re-run with different caps.
* **Source controls**: date range, academic-only mode, per-domain caps in UI.
* **Observability**: structured JSON traces; OpenTelemetry export.
* **Attachments**: user PDFs/URLs as seed docs.
* **Team mode**: API endpoint `/run` with key-based auth; lightweight role flags.

**Acceptance criteria**

* Repeatability: two identical runs vary only in sources that changed.
* Throughput: handle 5 concurrent runs without timeouts.
* API documented with examples.

### Stage 4 — Product polish (“fastest deep research”)

**Scope**

* **Web app**: Next.js + Tailwind + shadcn/ui + Framer Motion.

  * Multi-tab sessions, live trace panel, progress timeline.
  * Inline citation preview (hover to see source snippet).
  * “Evidence map” view: claims on left, sources on right; coverage heatmap.
  * One-click exports: Markdown, PDF, DOCX, JSON (with claim→URL map).
* **Speed**

  * Parallel search+fetch; smart early-write while reading continues.
  * Aggressive caching; warm start under 90 sec for typical briefs.
  * Cerebras streaming at \~3,000 tok/s output where supported. ([Cerebras][3])
* **Safety**

  * Respect robots.txt; user agent string; per-site request caps.
  * Citation integrity checker (random spot-check quotes vs sources).
* **Integrations**

  * Plug-in search providers (Tavily/Bing/Brave).
  * Optional import from open deep-research frameworks to compare outputs. ([GitHub][5], [LangChain Blog][6])
* **Admin**

  * Org settings: domain allowlists, default caps, model selection.
  * Usage dashboard: runs, tokens, cost.

**Acceptance criteria**

* UX: new user can run and export a credible brief in <2 min.
* Coverage: ≥90% non-obvious claims have ≥1 source; ≥60% have ≥2.
* Post-run report shows sources, costs, and time saved.

---

## 7) Architecture

**Runtime**

* Client UI → Backend service (`/run`) → Agent loop → Cerebras chat API (OpenAI-compatible) + search/fetch tools → SQLite cache → Storage (reports). ([inference-docs.cerebras.ai][1])

**Key components**

* **Planner**: break topic into sub-questions; propose queries.
* **Searcher**: call search API; return top-k results.
* **Reader**: fetch and extract text; split into chunks.
* **Analyst**: synthesize; track claim→source links.
* **Verifier**: find unsupported claims; trigger follow-up queries.
* **Writer**: produce final Markdown with references.

---

## 8) Data model (add Pydantic in Stage 2+)

* `SearchResult { title, url, snippet }`
* `Document { url, title, text, source_meta }`
* `Chunk { doc_url, text, hash, tokens }`
* `Claim { id, text, type, confidence }`
* `Citation { claim_id, urls[] }`
* `Report { topic, outline, sections[], citations[], references[] }`
* `TraceEvent { ts, kind, payload }`
* `Config { search_provider, k, max_rounds, caps, timeouts }`

---

## 9) APIs

**POST /run**

* Body: `{ topic, constraints?, config? }`
* Returns: `{ report_md, report_json, metrics: { duration_s, tokens_in, tokens_out, cost_est } }`

**GET /runs/\:id**

* Returns prior result + trace.

---

## 10) UI/UX (by stage)

**MVP (Streamlit)**

* Text area, “Run”, status log, Markdown output, download buttons.

**Stage 3–4 (Next.js)**

* Left: plan + logs + errors. Right: live draft + citations.
* Evidence map view; toggle academic-only; date range filter.
* Keyboard: Cmd/Ctrl+Enter to run; Shift+Enter new line.

---

## 11) Evaluation

**Harness**

* 10 fixed topics (mix of technical, policy, biomedical).
* Metrics: time, tokens, sources count, domain diversity, dead-link rate, claim coverage, duplication.
* Weekly regression run; threshold alarms on drops.

**Benchmarks (optional)**

* Compare outputs with open deep-research frameworks for sanity. ([GitHub][5], [LangChain Blog][6])

---

## 12) Security & compliance

* Respect robots.txt and site terms.
* Don’t store raw pages unless cached; store extracted text + URL + hash.
* Mask secrets; rotate keys; no keys in code.
* PII: avoid collecting; if user uploads docs, store encrypted at rest.
* Logs: redact URLs with tokens/auth params.

---

## 13) Operations

* Env: `.env` for keys and caps.
* Observability: JSON logs, request IDs, OpenTelemetry traces.
* Backpressure: queue runs; reject >N concurrent jobs with clear errors.
* Cost guardrails: per-run token ceilings; org caps.

---

## 14) Risks and mitigations

* **Paywalls / anti-bot** → rely on summaries, public alternates, or user-provided PDFs.
* **Source spam** → domain quality scores + allow/deny lists.
* **Hallucinated citations** → verify URLs resolve; quote-match spot checks.
* **Provider changes** → abstraction layer for search; health checks.
* **Cost overruns** → enforce ceilings; show cost estimates before run.

---

## 15) Implementation plan

**Week 1–2 (Stage 1)**

* Wire Cerebras client; build basic tools; Streamlit UI; simple claim coverage.
* Ship MVP.

**Week 3–4 (Stage 2)**

* Async fetch, caching, dedupe, quality gates, Pydantic, eval harness.

**Week 5–6 (Stage 3)**

* LangGraph orchestration, project workspaces, API, telemetry, attachments.

**Week 7–8 (Stage 4)**

* Next.js app, evidence map, exports, admin, polish, performance passes.

---

## 16) Tech stack

* **Backend**: Python 3.11, OpenAI SDK (pointed at Cerebras), httpx, trafilatura, pypdf, sqlite3.
* **Optional**: Pydantic v2, LangGraph, rapidfuzz/datasketch, BeautifulSoup.
* **UI**: Streamlit (MVP), Next.js + Tailwind + shadcn + Framer (Stage 4).
* **Infra**: Cerebras Inference Cloud; later on-prem possible.

---

## 17) References

* Cerebras: **gpt-oss-120B** at \~3,000 tok/s; launch details. ([Cerebras][3], [Inside HPC & AI News][4])
* OpenAI compatibility docs (use OpenAI client with Cerebras). ([inference-docs.cerebras.ai][1])
* Pricing model (pay-as-you-go overview). ([Cerebras][8])
* Open deep-research frameworks to borrow patterns or compare. ([GitHub][5], [LangChain Blog][6], [FlowiseAI][7])

---

### Notes on Pydantic

You don’t need it for MVP. It becomes valuable at Stage 2 for clean schemas, validation, and stable JSON exports.

If you want, I can turn this into a repo skeleton with `requirements.txt`, `.env.example`, and stubbed modules for each stage.

[1]: https://inference-docs.cerebras.ai/resources/openai?utm_source=chatgpt.com "OpenAI Compatibility - Build with Cerebras Inference"
[2]: https://www.cerebras.ai/blog/cerebras-launches-openai-s-gpt-oss-120b-at-a-blistering-3-000-tokens-sec?utm_source=chatgpt.com "Cerebras Launches OpenAI's gpt-oss-120B at a Blistering ..."
[3]: https://www.cerebras.ai/news/cerebras-helps-power-openai-s-open-model-at-world-record-inference-speeds-gpt-oss-120b-delivers?utm_source=chatgpt.com "gpt-oss-120B Delivers Frontier Reasoning for All"
[4]: https://insidehpc.com/2025/08/cerebras-reports-3000-tokens-per-second-inference-on-openai-gpt-oss-120b-model/?utm_source=chatgpt.com "Cerebras Reports 3,000 Tokens Per Second Inference on ..."
[5]: https://github.com/langchain-ai/open_deep_research?utm_source=chatgpt.com "langchain-ai/open_deep_research"
[6]: https://blog.langchain.com/open-deep-research/?utm_source=chatgpt.com "Open Deep Research"
[7]: https://docs.flowiseai.com/tutorials/deep-research?utm_source=chatgpt.com "Deep Research | FlowiseAI"
[8]: https://www.cerebras.ai/inference?utm_source=chatgpt.com "Get Instant AI Inference"