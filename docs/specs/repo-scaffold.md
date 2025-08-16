# Repository Scaffold Plan — Deep Research Agent

2025-08-15 20:26:57 - Initial version. Defines the directory structure, initial files, stub mappings, and kickoff checklist to begin implementation cleanly.

References:
- PRD: [../prd.md](../prd.md)
- Master Plan: [../master-plan.md](../master-plan.md)
- Module Specs: [./module-specs.md](./module-specs.md)
- API Contract: [./api-contract.md](./api-contract.md)
- Data Schemas: [./data-schemas.md](./data-schemas.md)
- Observability: [./observability-logging.md](./observability-logging.md)
- Security: [./security-compliance.md](./security-compliance.md)
- Ops Runbook: [./ops-runbook.md](./ops-runbook.md)
- Evaluation Harness: [./evaluation-harness.md](./evaluation-harness.md)
- Memory Bank:
  - [../../memory-bank/productContext.md](../../memory-bank/productContext.md)
  - [../../memory-bank/activeContext.md](../../memory-bank/activeContext.md)
  - [../../memory-bank/progress.md](../../memory-bank/progress.md)
  - [../../memory-bank/decisionLog.md](../../memory-bank/decisionLog.md)
  - [../../memory-bank/systemPatterns.md](../../memory-bank/systemPatterns.md)

---

## 1) Directory structure (target)

Top-level layout for MVP through Stage 3 (folders may be created incrementally):

- docs/
  - prd.md
  - master-plan.md
  - specs/
    - module-specs.md
    - api-contract.md
    - data-schemas.md
    - evaluation-harness.md
    - observability-logging.md
    - security-compliance.md
    - ops-runbook.md
    - repo-scaffold.md
- src/
  - app.py
  - agent/
    - planner.py
    - searcher.py
    - reader.py
    - analyst.py
    - verifier.py
    - writer.py
  - tools/
    - web_search.py
    - fetch_url.py
    - parse_pdf.py
  - providers/
    - cerebras_client.py
    - search_providers.py
  - storage/
    - cache.py
    - models.py
  - api/
    - service.py
  - observability/
    - __init__.py
    - logging.py
    - tracing.py
- eval/
  - harness.py
  - topics.json
- exports/       (generated artifacts)
- data/          (Stage 2+ cache.sqlite, if enabled)
- tests/         (placeholder for later)
- .env.example
- requirements.txt
- README.md

---

## 2) File purposes and initial stub responsibilities

MVP-core:
- [src/app.py](../../src/app.py) — Streamlit UI shell and local runner:
  - Input topic/constraints, show logs, render Markdown report, download .md
  - Calls into agent loop orchestrator
- Agent components:
  - [src/agent/planner.py](../../src/agent/planner.py) — [`planner.plan()`](../../src/agent/planner.py:1)
  - [src/agent/searcher.py](../../src/agent/searcher.py) — [`searcher.search()`](../../src/agent/searcher.py:1)
  - [src/agent/reader.py](../../src/agent/reader.py) — [`reader.read()`](../../src/agent/reader.py:1)
  - [src/agent/analyst.py](../../src/agent/analyst.py) — [`analyst.analyze()`](../../src/agent/analyst.py:1)
  - [src/agent/verifier.py](../../src/agent/verifier.py) — [`verifier.verify()`](../../src/agent/verifier.py:1)
  - [src/agent/writer.py](../../src/agent/writer.py) — [`writer.write()`](../../src/agent/writer.py:1)
- Tools (I/O functions):
  - [src/tools/web_search.py](../../src/tools/web_search.py) — [`web_search.run()`](../../src/tools/web_search.py:1)
  - [src/tools/fetch_url.py](../../src/tools/fetch_url.py) — [`fetch_url.run()`](../../src/tools/fetch_url.py:1)
  - [src/tools/parse_pdf.py](../../src/tools/parse_pdf.py) — [`parse_pdf.run()`](../../src/tools/parse_pdf.py:1)
- Providers (clients/abstractions):
  - [src/providers/cerebras_client.py](../../src/providers/cerebras_client.py) — [`cerebras_client.chat()`](../../src/providers/cerebras_client.py:1)
  - [src/providers/search_providers.py](../../src/providers/search_providers.py) — [`search_providers.duckduckgo()`](../../src/providers/search_providers.py:1)
- Storage and models:
  - [src/storage/models.py](../../src/storage/models.py) — Pydantic v2 models in Stage 2; MVP typed dicts
  - [src/storage/cache.py](../../src/storage/cache.py) — SQLite cache in Stage 2
- API (Stage 3):
  - [src/api/service.py](../../src/api/service.py) — [`service.run()`](../../src/api/service.py:1), [`service.get_run()`](../../src/api/service.py:1)
- Observability:
  - [src/observability/logging.py](../../src/observability/logging.py) — [`logging.get_logger()`](../../src/observability/logging.py:1)
  - [src/observability/tracing.py](../../src/observability/tracing.py) — [`tracing.emit_event()`](../../src/observability/tracing.py:1)

Evaluation:
- [eval/harness.py](../../eval/harness.py) — batch evaluator runner
- [eval/topics.json](../../eval/topics.json) — the 10-topic seed list

Artifacts:
- exports/ — saved reports, metrics, traces from runs

---

## 3) Initial content guidance

3.1 requirements.txt (MVP)
- streamlit
- openai
- httpx
- trafilatura
- pypdf
- tldextract
- python-dotenv
- tenacity
- (Stage 2+) pydantic>=2,<3
- (Stage 2+) sqlite-utils or equivalent
- (Stage 3+) fastapi uvicorn (if service mode chosen)
- (Stage 3+) opentelemetry-api opentelemetry-sdk (optional)

3.2 .env.example
- CEREBRAS_API_KEY=
- CEREBRAS_BASE_URL=https://api.cerebras.ai/v1
- MODEL=gpt-oss-120b
- SEARCH_PROVIDER=duckduckgo
- MAX_ROUNDS=3
- PER_DOMAIN_CAP=3
- FETCH_TIMEOUT_S=15
- ENABLE_CACHE=false
- LOG_LEVEL=INFO
- USER_AGENT=NovaBrief-Research/0.1

3.3 README.md (outline)
- Overview and goals (link PRD)
- Quickstart (install, env setup, run)
- Usage (Streamlit UI)
- Configuration (env vars)
- Roadmap (Stages 1–4)
- Links to specs

---

## 4) Orchestration notes (MVP)

- app.py coordinates the loop:
  - Call [`planner.plan()`](../../src/agent/planner.py:1) → queries
  - Call [`searcher.search()`](../../src/agent/searcher.py:1) → SearchResult[]
  - Call [`reader.read()`](../../src/agent/reader.py:1) → Document[] + Chunk[]
  - Call [`analyst.analyze()`](../../src/agent/analyst.py:1) → claims, interim citations, draft sections
  - Call [`verifier.verify()`](../../src/agent/verifier.py:1) → unsupported claims, follow-up queries
  - Iterate until coverage or budget exhausted
  - Call [`writer.write()`](../../src/agent/writer.py:1) → report_md + references
- Logging:
  - Use [`logging.get_logger()`](../../src/observability/logging.py:1)
  - Emit TraceEvent via [`tracing.emit_event()`](../../src/observability/tracing.py:1)

---

## 5) Kickoff: file stub checklist

MVP stubs to create during coding kickoff:
- [src/app.py](../../src/app.py) — Streamlit entry with textbox, “Run”, logs, output pane
- [src/agent/planner.py](../../src/agent/planner.py) — skeleton with [`planner.plan()`](../../src/agent/planner.py:1)
- [src/agent/searcher.py](../../src/agent/searcher.py) — skeleton with [`searcher.search()`](../../src/agent/searcher.py:1)
- [src/agent/reader.py](../../src/agent/reader.py) — skeleton with [`reader.read()`](../../src/agent/reader.py:1)
- [src/agent/analyst.py](../../src/agent/analyst.py) — skeleton with [`analyst.analyze()`](../../src/agent/analyst.py:1)
- [src/agent/verifier.py](../../src/agent/verifier.py) — skeleton with [`verifier.verify()`](../../src/agent/verifier.py:1)
- [src/agent/writer.py](../../src/agent/writer.py) — skeleton with [`writer.write()`](../../src/agent/writer.py:1)
- [src/tools/web_search.py](../../src/tools/web_search.py), [`web_search.run()`](../../src/tools/web_search.py:1)
- [src/tools/fetch_url.py](../../src/tools/fetch_url.py), [`fetch_url.run()`](../../src/tools/fetch_url.py:1)
- [src/tools/parse_pdf.py](../../src/tools/parse_pdf.py), [`parse_pdf.run()`](../../src/tools/parse_pdf.py:1)
- [src/providers/cerebras_client.py](../../src/providers/cerebras_client.py), [`cerebras_client.chat()`](../../src/providers/cerebras_client.py:1)
- [src/providers/search_providers.py](../../src/providers/search_providers.py), [`search_providers.duckduckgo()`](../../src/providers/search_providers.py:1)
- [src/observability/logging.py](../../src/observability/logging.py), [`logging.get_logger()`](../../src/observability/logging.py:1)
- [src/observability/tracing.py](../../src/observability/tracing.py), [`tracing.emit_event()`](../../src/observability/tracing.py:1)
- [requirements.txt](../../requirements.txt)
- [.env.example](../../.env.example)
- [eval/harness.py](../../eval/harness.py), [eval/topics.json](../../eval/topics.json)

---

## 6) Coding standards and guardrails

- Pure function boundaries; side effects isolated in tools/providers
- Validation of inputs per [./api-contract.md](./api-contract.md) and [./data-schemas.md](./data-schemas.md)
- Respect robots.txt; redact sensitive params in logs (see [./security-compliance.md](./security-compliance.md))
- Deterministic logs/traces; avoid printing plain strings

---

## 7) Implementation order for MVP

1) Providers:
   - [`cerebras_client.chat()`](../../src/providers/cerebras_client.py:1)
   - [`search_providers.duckduckgo()`](../../src/providers/search_providers.py:1)
2) Tools:
   - [`web_search.run()`](../../src/tools/web_search.py:1)
   - [`fetch_url.run()`](../../src/tools/fetch_url.py:1)
   - [`parse_pdf.run()`](../../src/tools/parse_pdf.py:1)
3) Agent core:
   - [`planner.plan()`](../../src/agent/planner.py:1)
   - [`searcher.search()`](../../src/agent/searcher.py:1)
   - [`reader.read()`](../../src/agent/reader.py:1)
   - [`analyst.analyze()`](../../src/agent/analyst.py:1)
   - [`verifier.verify()`](../../src/agent/verifier.py:1)
   - [`writer.write()`](../../src/agent/writer.py:1)
4) UI:
   - [src/app.py](../../src/app.py) Streamlit wrapper, logging panel, markdown output
5) Evaluation smoke:
   - [eval/harness.py](../../eval/harness.py) run on 3 topics

---

## 8) Coding kickoff checklist

- [ ] Create requirements.txt and install
- [ ] Create .env.example; set CEREBRAS_API_KEY locally
- [ ] Implement providers and tools with simple tests
- [ ] Implement agent functions with minimal logic per [./module-specs.md](./module-specs.md)
- [ ] Wire Streamlit UI and produce first report_md
- [ ] Export report to exports/ and record metrics
- [ ] Run mini evaluation on 3 topics; confirm MVP acceptance targets
- [ ] Update Memory Bank: planning completion and coding start

---

## 9) Change control

Any structural change to repository layout or core file responsibilities:
- Update this document
- Reflect in master-plan and Memory Bank [../../memory-bank/decisionLog.md](../../memory-bank/decisionLog.md)