# Phase 4 — Self-Correcting Generation and Advanced Evaluation Loop

Purpose
- Implement a self-correcting pipeline where generation quality is improved before finalization (Critic-in-the-loop), and then measured with a rigorous LLM-as-Judge evaluation harness using the same rubric.
- Produce both JSON results and a professional PDF summary report from the evaluation harness.

Scope
- Critic agent: upgrade to act as an editorial reviewer that can gate or request revisions before publish.
- Orchestrator: wire a two-pass writing workflow (draft → critique → revise if needed → finalize).
- Harness: add rubric-based semantic scoring (LLM-as-Judge), retain legacy coverage metrics if useful for trend comparison.
- PDF generator: produce an executive-friendly report summarizing evaluation metrics.

References to code
- Critic agent already exists and can be extended: [src/agent/critic.py](src/agent/critic.py:1)
- Orchestrator wiring location: [src/agent/orchestrator.py](src/agent/orchestrator.py:1)
- Writer agent (first-draft and revision calls): [src/agent/writer.py](src/agent/writer.py:1)
- Current evaluation harness entry: [eval/harness.py](eval/harness.py:1)
- Multi-model harness: [eval/multi_model_harness.py](eval/multi_model_harness.py:1)

Unified Quality Rubric (single source of truth)
- Maintain one rubric that both the Critic and the Judge use. This ensures alignment between what the system optimizes for and how it is judged.
- Core criteria (adapted from the prompt and aligned to existing artifacts):
  - Comprehensiveness: Does the brief address the initial sub-questions generated in planning?
  - Synthesis & Depth: Does it integrate facts into a coherent, insight-rich narrative vs. listing?
  - Clarity & Coherence: Is it well-structured, readable, logically organized for the target audience?
  - Source Reliability and Evidence: Are claims supported with credible references (optional to include in Judge v1; already covered by pipeline’s verification stage)?
- Storage/Access:
  - Place a rubric definition helper in eval/rubric.py (new) that exports:
    - critic_prompt_fragments (JSON-only format instructions, criteria text)
    - judge_prompt_fragments (JSON-only format instructions, criteria text)
  - Critic and Judge modules import shared rubric fragments to keep parity.

Part A — Critic Agent: In-Process Refinement

A1) Critic review function
- Update Critic to expose:
  - review(draft_report: str, state: Dict[str, Any], target_audience: str) -> Dict[str, Any]
    - Returns JSON with:
      - is_publishable: bool
      - revisions_needed: list[str] (actionable revision instructions)
      - rubric_notes: optional dict with short notes by criterion
- Where to implement:
  - Add a new function review(...) alongside existing critique_report in [src/agent/critic.py](src/agent/critic.py:1)
  - Keep critique_report(...) for Phase 3 compatibility; use review(...) for gating step

A2) Prompts for the Critic
- System prompt (JSON-only):
  - See template in docs/prompts/eval-upgrades.md; enforce strict JSON output:
    {
      "is_publishable": boolean,
      "revisions_needed": ["Specific revision instruction 1.", "Specific revision instruction 2."]
    }
- User prompt should include:
  - Brief context: research topic, target audience
  - Sub-questions list (from planning)
  - Draft report content
  - Short rubric text (from eval/rubric.py)

A3) Critic execution details
- Model & parameters:
  - Use agent policy routing as introduced in Phase 3. For routing mode policy/hybrid, resolve critic model via [Config.get_agent_model("critic", pref, target_audience)](src/config.py:523) and parameters via [Config.get_agent_parameters("critic", target_audience)](src/config.py:587).
  - Pass model_key to provider chat calls once model override is added in Phase 3 wiring.
- Robust JSON parsing:
  - Mirror writer’s defensive parsing approach in [writer._generate_report_content()](src/agent/writer.py:238) to extract valid JSON even if the LLM returns text with code fences.
- Failure handling:
  - On malformed response: return is_publishable=False with a generic “retry formatting” revision.
  - On provider error: fall back to publishable=True to avoid dead-ends, but log a warning.

Part B — Orchestrator: Two-Stage Writing

B1) Two-pass flow
- After analysis/verification:
  - Stage 6: Writer produces Draft-1 (as it does now) [orchestrator.write stage](src/agent/orchestrator.py:418)
  - Stage 7: Critic review gate
    - Call critic.review(draft_report, state, target_audience)
    - If is_publishable=false and revisions_needed non-empty:
      - Construct a revision_context (compact, actionable) and call writer again to produce Draft-2
      - Else, accept Draft-1 as final
  - Stage 8: Finalize and continue to any post-processing (evidence map, UI, etc.)

B2) Data passed to Critic
- Provide:
  - topic
  - target_audience
  - sub_questions
  - draft_report.report_md
  - optionally, coverage metrics and documents count to assist qualitative decisions

B3) Logging and telemetry
- Emit events:
  - "critic_started" (with counts and metadata)
  - "critic_completed" (with is_publishable and revision count)
  - "writer_revision_started" and "writer_revision_completed" if a second pass occurs

Part C — LLM-as-Judge: Advanced Evaluation in Harness

C1) Judge module/function
- Create helper eval/judge.py (new):
  - def score_report(report_markdown: str, sub_questions: list[str]) -> dict:
    - Returns:
      {
        "comprehensiveness_score": float (0.0-1.0),
        "synthesis_score": float (0.0-1.0),
        "clarity_score": float (0.0-1.0),
        "overall_quality_score": float (e.g., weighted average),
        "justification": "brief rationale"
      }
  - Use the same rubric fragments from eval/rubric.py; enforce strict JSON response.
  - Implement robust parsing and safe fallbacks as with Critic/Writer.

C2) Harness integration
- In [eval/harness.py](eval/harness.py:1):
  - Replace or extend the current evaluation step (e.g., _evaluate_content_coverage) with:
    - _evaluate_semantic_quality(report, sub_questions) → uses eval/judge.score_report
  - Preserve legacy metrics for longitudinal comparison; add new semantic scores to the results payload.

C3) Multi-model evaluation
- In [eval/multi_model_harness.py](eval/multi_model_harness.py:1):
  - Ensure runs capture:
    - overall_quality_score per model
    - criterion-level scores (comprehensiveness, synthesis, clarity)
    - optional timing/cost if available
  - Compute aggregate statistics across topics:
    - mean and variance per metric per model

Part D — PDF Evaluation Report

D1) Dependency
- Add fpdf2 (or weasyprint/reportlab) in pyproject:
  - uv add fpdf2
- Keep PDF generator UI/CLI neutral.

D2) Report generator module
- New file: eval/report_generator.py
- Function:
  - create_pdf_report(eval_results: dict, output_filename: str) -> None
- Structure:
  - Title page: "Nova Brief Evaluation Report", timestamp
  - Executive Summary:
    - Overall Quality Leader(s)
    - Average Overall Quality Score by model
  - Comparison Table:
    - Model, Overall Quality, Comprehensiveness, Synthesis, Clarity, Avg duration (if recorded), Notes
  - Detailed sections:
    - Per-model breakdown with horizontal bar charts (optional ASCII or simple tables if graphical complexity is out-of-scope for fpdf2 v1)
- Styling:
  - Clean typography, consistent headers, footers with page numbers.

D3) Harness integration
- At end of [eval/harness.py](eval/harness.py:1):
  - After saving JSON: call create_pdf_report(results, output_path.replace(".json", ".pdf"))
- Ensure failures to generate PDF don’t fail the evaluation run (log warning).

Part E — Implementation Steps (ordered)

E1) Rubric source and prompt fragments
- Create eval/rubric.py:
  - Export CRITIC_SYSTEM_PROMPT, CRITIC_USER_RUBRIC_TEMPLATE
  - Export JUDGE_SYSTEM_PROMPT, JUDGE_USER_RUBRIC_TEMPLATE
  - Keep templates minimal and JSON-only, with clear placeholders:
    - {list_of_sub_questions}
    - {draft_report_content} / {final_report_content}

E2) Critic review function
- Add review(...) to [src/agent/critic.py](src/agent/critic.py:1)
- Implement prompt assembly using rubric fragments.
- Add robust JSON parse + fallbacks; return dict structure as specified above.

E3) Orchestrator wiring
- In [src/agent/orchestrator.py](src/agent/orchestrator.py:1):
  - After writing stage, insert critic review step:
    - If revisions_needed: call writer again with revision context (brief actionable bullet points)
  - Ensure target_audience is passed consistently through stages.
  - Emit structured events and logs.

E4) Provider integration (Phase 3 dependency)
- Ensure provider client supports model_key override:
  - openrouter_client.chat(..., model_key="...") — see [src/providers/openrouter_client.py](src/providers/openrouter_client.py:32)
- For policy/hybrid routing, look up model for Critic via [Config.get_agent_model](src/config.py:523).

E5) Judge integration in harness
- Create eval/judge.py and wire into [eval/harness.py](eval/harness.py:1)
- Replace current coverage-only scoring with rubric-based semantic scoring:
  - Evaluate each final report with Judge; add scores to results JSON.

E6) PDF generator
- Add eval/report_generator.py with create_pdf_report(...)
- Hook call from harness after JSON is produced.

E7) Documentation
- Update:
  - docs/master-plan.md to reflect Critic-in-the-loop + LLM-as-Judge + PDF reporting
  - docs/specs/evaluation-harness.md to include rubric, judge prompts, score schema, and PDF output
  - README: short section “Evaluation Outputs” and how to open the PDF

E8) Tests
- Unit tests:
  - Judge JSON parsing robustness (mock LLM responses)
  - Critic review JSON parsing (malformed → fallback)
  - Report generator smoke test: valid PDF bytes written and non-zero size
- CLI tests:
  - Quick harness run with a tiny topic set; assert JSON contains new fields and PDF exists

Part F — Prompts (grounded in docs/prompts/eval-upgrades.md)

F1) Critic system prompt (JSON-only)
- As per the master prompt; enforce exact keys is_publishable (bool) and revisions_needed (list of strings).
- Place base version in eval/rubric.py; import in critic.

F2) Critic user prompt
- Provide sub-questions, draft report, and rubric criteria. Keep concise to control tokens.

F3) Judge system prompt (JSON-only)
- As per master prompt with float scores in [0.0, 1.0] and a short justification.

F4) Judge user prompt
- Provide final report content and sub-questions; reuse the same rubric text for parity with Critic.

Part G — Rollout Plan

G1) Phase 4.1 (minimal risk)
- Add Judge + rubric and integrate into harness (read-only change to main pipeline).
- Produce PDF evaluation report.
- No changes to app runtime behavior yet.

G2) Phase 4.2 (enable Critic gate)
- Activate Critic review in orchestrator with safe fallbacks.
- Enable Writer revision pass only when revisions_needed are specific and small (cap at e.g., max 2 revisions).

G3) Phase 4.3 (optimize)
- Tune rubric wording and weighting based on evaluation distribution.
- Add optional cost/time metrics to PDF (if available).

Operational Notes
- Env/deps:
  - uv add fpdf2
  - Keep provider keys in .env as-is.
- Token budgeting:
  - Keep rubric text compact.
  - Limit sub-questions passed to Judge/Critic user prompts (top-N).
- Failure safety:
  - If Judge fails, write JSON with graceful defaults and skip PDF (or generate with partial data).
  - If Critic fails, assume publishable and proceed.

Deliverables
- New modules:
  - eval/rubric.py
  - eval/judge.py
  - eval/report_generator.py
- Updated modules:
  - src/agent/critic.py (add review)
  - src/agent/orchestrator.py (insert Critic gate and optional Writer revision)
  - eval/harness.py (semantic scoring, PDF call)
- Docs:
  - This document (Phase 4)
  - Updated specs: evaluation harness and master plan

Acceptance Criteria
- Running the harness produces:
  - JSON with semantic scores: comprehensiveness, synthesis, clarity, overall_quality, and justification
  - A PDF summary with title, executive summary, comparison table, and model breakdowns
- Running the app yields:
  - Two-pass writing when Critic requests revisions (configurable)
  - Stable behavior fallback if Critic or Judge fails
