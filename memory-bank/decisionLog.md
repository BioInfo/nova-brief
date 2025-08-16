# Decision Log

This file records architectural and implementation decisions using a list format.
2025-08-16 15:35:55 - Log of updates made.

*

## Decision

*

## Rationale 

*

## Implementation Details

*
[2025-08-16 15:38:10] - OpenRouter Integration Decision
- Decision: Route all LLM calls through OpenRouter’s OpenAI-compatible API, pinning provider to Cerebras and using model "openai/gpt-oss-120b".
- Rationale: Maintain Cerebras performance/throughput while standardizing on a single gateway; enable structured outputs via JSON Schema to reduce parsing errors.
- Implementation Details:
  - Docs updated: [docs/master-plan.md](docs/master-plan.md), [docs/prd.md](docs/prd.md), [docs/specs/repo-scaffold.md](docs/specs/repo-scaffold.md), [docs/specs/ops-runbook.md](docs/specs/ops-runbook.md), [docs/specs/module-specs.md](docs/specs/module-specs.md), [docs/specs/data-schemas.md](docs/specs/data-schemas.md), [docs/specs/security-compliance.md](docs/specs/security-compliance.md)
  - Env vars: OPENROUTER_API_KEY, OPENROUTER_BASE_URL=https://openrouter.ai/api/v1, MODEL="openai/gpt-oss-120b"
  - Provider pinning: include {"providers": ["cerebras"]} in request body
  - Structured output: Writer to pass Pydantic-derived JSON Schema via response_format/tool-calling