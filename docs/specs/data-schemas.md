# Data Schemas — Deep Research Agent

2025-08-15 20:22:39 - Initial version derived from PRD, master-plan, and module-specs. This document defines stable data contracts across the agent loop and API. Stage 1 uses lightweight typed dict-style contracts; Stage 2 upgrades to Pydantic v2 models and typed JSON exports.

References:
- PRD: [../prd.md](../prd.md)
- Master Plan: [../master-plan.md](../master-plan.md)
- Module Specs: [./module-specs.md](./module-specs.md)
- API Contract: [./api-contract.md](./api-contract.md)
- Planned model file: [../../src/storage/models.py](../../src/storage/models.py)
  - Class proposals: [`models.SearchResult()`](../../src/storage/models.py:1), [`models.Document()`](../../src/storage/models.py:1), [`models.Chunk()`](../../src/storage/models.py:1), [`models.Claim()`](../../src/storage/models.py:1), [`models.Citation()`](../../src/storage/models.py:1), [`models.Report()`](../../src/storage/models.py:1), [`models.TraceEvent()`](../../src/storage/models.py:1), [`models.Config()`](../../src/storage/models.py:1), [`models.Metrics()`](../../src/storage/models.py:1)

---

## 1) Versioning and stability

- Schema version: v0 (MVP), v1 (Stage 2 with Pydantic v2)
- Backward compatibility: additive where possible; breaking changes gated and documented
- JSON export: camelCase in API responses; internal Python uses snake_case fields

Version field:
- reports: `schema_version: "v0"` (MVP) → `"v1"` (Stage 2)

---

## 2) Core entities

2.1 SearchResult
- Purpose: output of search providers
- Fields (MVP):
  - title: string (≤ 256)
  - url: string (absolute http/https)
  - snippet: string (≤ 1024, optional)
- Example:
{
  "title": "Cerebras announcement",
  "url": "https://www.cerebras.ai/news/...",
  "snippet": "gpt-oss-120b delivers ~3,000 tok/s..."
}

2.2 Document
- Purpose: normalized, extracted content
- Fields:
  - url: string
  - title: string (optional)
  - text: string (main extracted content)
  - source_meta: { domain: string, lang?: string, content_type?: string }
- Example:
{
  "url": "https://insidehpc.com/2025/08/.../",
  "title": "Cerebras Reports 3,000 Tokens Per Second...",
  "text": "The system delivers ...",
  "source_meta": { "domain": "insidehpc.com", "lang": "en", "content_type": "text/html" }
}

2.3 Chunk
- Purpose: token-bounded segments for analysis
- Fields:
  - doc_url: string
  - text: string
  - hash: string (e.g., sha256 of normalized text)
  - tokens: number (≤ max_token_per_chunk)
- Example:
{
  "doc_url": "https://example.com/a",
  "text": "Segment...",
  "hash": "sha256:deadbeef...",
  "tokens": 972
}

2.4 Claim
- Purpose: structured assertions for verification
- Fields:
  - id: string (unique within run)
  - text: string
  - type: enum { "fact", "estimate", "opinion" }
  - confidence: number (0..1)
- Example:
{
  "id": "c1",
  "text": "GPT-OSS-120B delivers ~3,000 tok/s on Cerebras.",
  "type": "fact",
  "confidence": 0.9
}

2.5 Citation
- Purpose: claim-to-source linkage
- Fields:
  - claim_id: string
  - urls: string[] (absolute; de-duplicated; canonicalized)
- Example:
{
  "claim_id": "c1",
  "urls": [
    "https://www.cerebras.ai/news/...",
    "https://insidehpc.com/2025/08/..."
  ]
}

2.6 Report
- Purpose: final deliverable structure
- Fields:
  - topic: string
  - outline: string[]
  - sections: string[] (markdown segments)
  - citations: Citation[]
  - references: { n: number, url: string, title?: string }[]
  - schema_version: string ("v0" | "v1")
- Example:
{
  "topic": "X",
  "outline": ["Intro", "Findings", "Conclusion"],
  "sections": ["# Intro...", "## Findings...", "## Conclusion..."],
  "citations": [{"claim_id": "c1", "urls": ["https://..."]}],
  "references": [{"n": 1, "url": "https://..."}],
  "schema_version": "v0"
}

2.7 TraceEvent
- Purpose: observability events
- Fields:
  - ts: string (ISO 8601)
  - kind: enum {
      "tool_call", "search_result", "fetch_result",
      "chunk_made", "claim_made", "verify_result",
      "writer_finalized", "error"
    }
  - payload: object (free-form, schema per kind)
- Example:
{
  "ts": "2025-08-15T20:00:06Z",
  "kind": "fetch_result",
  "payload": { "url": "https://...", "status": 200, "bytes": 53211 }
}

2.8 Config
- Purpose: run configuration and caps
- Fields:
  - search_provider: enum { "duckduckgo", "tavily", "bing", "brave" }
  - k: number (3..10)
  - max_rounds: number (1..10)
  - per_domain_cap: number (1..10)
  - timeouts: { fetch_timeout_s: number (5..60) }
  - model: string ("openai/gpt-oss-120b" default)
  - openrouter_base_url: string
  - enable_cache: boolean
- Example:
{
  "search_provider": "duckduckgo",
  "k": 6,
  "max_rounds": 3,
  "per_domain_cap": 3,
  "timeouts": { "fetch_timeout_s": 15 },
  "model": "openai/gpt-oss-120b",
  "openrouter_base_url": "https://openrouter.ai/api/v1",
  "enable_cache": false
}

2.9 Metrics
- Purpose: run-level KPIs
- Fields:
  - duration_s: number
  - tokens_in: number
  - tokens_out: number
  - cost_est: number
  - sources_count: number
  - domain_diversity: number
  - cache_hits: number
  - cache_misses: number
- Example:
{
  "duration_s": 241.2,
  "tokens_in": 10234,
  "tokens_out": 8361,
  "cost_est": 0.98,
  "sources_count": 9,
  "domain_diversity": 7,
  "cache_hits": 0,
  "cache_misses": 12
}

---

## 3) Field constraints and normalization

- url: must start with http:// or https://; normalized (scheme, host lowercase, strip default ports, resolve ../)
- domain: extracted from url; punycode normalized
- tokens: computed using the model’s tokenizer approximation; Stage 2 standardize via a shared utility
- text: normalized newlines to \n; strip control characters
- ids: run-unique prefix (e.g., c1, c2...) for claims

Validation (Stage 2, Pydantic v2):
- String lengths, enums, numeric ranges enforced
- Custom validators for URL normalization and domain extraction

3.5) Structured Output Generation
- The Writer component will leverage the Pydantic models defined in Stage 2 to generate a JSON Schema. This schema will be passed to the OpenRouter API to request a response that strictly conforms to the Report data model. This moves from a "prompt engineering" approach for JSON to a more reliable, "schema-driven" approach.

Example Writer logic:
- Get Pydantic model Report.
- Generate schema: Report.model_json_schema().
- Pass schema to the chat() call using the response_format parameter with type: "json_object" and the relevant tool-calling structure for JSON Schema enforcement.
---

## 4) Relationships and invariants

- Every non-obvious Claim must appear in at least one Citation.urls
- References: ordered by first appearance in the final Markdown (1..N)
- Citations: deduplicate mirrored domains (e.g., m.example.com vs www.example.com) for diversity metrics
- Chunk.doc_url must exist in Documents
- Report.sections length must align with Report.outline (best-effort alignment; not strictly required)

---

## 5) JSON export shapes (API)

- Use camelCase in responses
- Include schemaVersion on Report and potentially on other objects in Stage 2+

Example (excerpt):
{
  "reportJson": {
    "topic": "Example",
    "sections": ["# Intro...", "..."],
    "citations": [{"claimId": "c1", "urls": ["https://..."]}],
    "references": [{"n": 1, "url": "https://..."}],
    "schemaVersion": "v1"
  }
}

---

## 6) Stage 2 Pydantic v2 model proposals (Python)

Target file: [../../src/storage/models.py](../../src/storage/models.py)

- [`models.SearchResult()`](../../src/storage/models.py:1)
  - title: constr(max_length=256)
  - url: AnyUrl
  - snippet: constr(max_length=1024) | None

- [`models.Document()`](../../src/storage/models.py:1)
  - url: AnyUrl
  - title: str | None
  - text: str
  - source_meta: dict[str, Any]  # domain, lang, content_type

- [`models.Chunk()`](../../src/storage/models.py:1)
  - doc_url: AnyUrl
  - text: str
  - hash: constr(min_length=8, max_length=200)
  - tokens: int

- [`models.Claim()`](../../src/storage/models.py:1)
  - id: constr(min_length=1, max_length=40)
  - text: str
  - type: Literal["fact", "estimate", "opinion"]
  - confidence: confloat(ge=0.0, le=1.0)

- [`models.Citation()`](../../src/storage/models.py:1)
  - claim_id: str
  - urls: list[AnyUrl]

- [`models.Reference()`](../../src/storage/models.py:1)
  - n: int
  - url: AnyUrl
  - title: str | None

- [`models.Report()`](../../src/storage/models.py:1)
  - topic: str
  - outline: list[str]
  - sections: list[str]
  - citations: list[["Citation"]]  # forward ref
  - references: list[["Reference"]]
  - schema_version: Literal["v0", "v1"]

- [`models.TraceEvent()`](../../src/storage/models.py:1)
  - ts: datetime
  - kind: Literal[
      "tool_call", "search_result", "fetch_result",
      "chunk_made", "claim_made", "verify_result",
      "writer_finalized", "error"
    ]
  - payload: dict[str, Any]

- [`models.Config()`](../../src/storage/models.py:1)
  - search_provider: Literal["duckduckgo", "tavily", "bing", "brave"]
  - k: conint(ge=3, le=10)
  - max_rounds: conint(ge=1, le=10)
  - per_domain_cap: conint(ge=1, le=10)
  - timeouts: dict[str, int]  # fetch_timeout_s validated elsewhere
  - model: str
  - cerebras_base_url: AnyUrl
  - enable_cache: bool

- [`models.Metrics()`](../../src/storage/models.py:1)
  - duration_s: float
  - tokens_in: int
  - tokens_out: int
  - cost_est: float
  - sources_count: int
  - domain_diversity: int
  - cache_hits: int
  - cache_misses: int

---

## 7) Serialization and storage

- Stage 2 SQLite:
  - pages(url TEXT PRIMARY KEY, text BLOB, title TEXT, domain TEXT, lang TEXT, content_type TEXT, hash TEXT, ts DATETIME)
  - traces(id TEXT, ts DATETIME, kind TEXT, payload JSON)
  - runs(id TEXT PRIMARY KEY, topic TEXT, report_md BLOB, report_json JSON, metrics JSON, created_at DATETIME)
- JSON dumps: ensure UTF-8; large fields compressed where needed

---

## 8) Tokenization and chunking utilities

- Shared utility proposed: [`storage.tokenize_chunk()`](../../src/storage/models.py:1)
  - Inputs: text, target_tokens, overlap
  - Output: list[Chunk]
- Deterministic across runs for same inputs

---

## 9) Validation rules summary

- URLs absolute and normalized
- Claims must be linked to at least one citation before finalization
- References numbers sequential and unique
- Metrics fields non-negative
- Config within bounded ranges (see API contract)

---

## 10) Change control

- All schema changes must:
  - Update this document
  - Update [./api-contract.md](./api-contract.md) if API visible
  - Update Memory Bank: [../../memory-bank/decisionLog.md](../../memory-bank/decisionLog.md) with summary, rationale, implications