"""
Unified Quality Rubric for Nova Brief - Single source of truth for both Critic and Judge.

This module provides shared rubric fragments that ensure alignment between 
what the Critic optimizes for and how the Judge evaluates reports.
"""

# Core quality criteria aligned with Phase 4 requirements
QUALITY_CRITERIA = {
    "comprehensiveness": {
        "name": "Comprehensiveness",
        "description": "Does the brief address the initial sub-questions generated in planning?",
        "weight": 0.3
    },
    "synthesis": {
        "name": "Synthesis & Depth", 
        "description": "Does it integrate facts into a coherent, insight-rich narrative vs. listing?",
        "weight": 0.3
    },
    "clarity": {
        "name": "Clarity & Coherence",
        "description": "Is it well-structured, readable, logically organized for the target audience?",
        "weight": 0.25
    },
    "evidence": {
        "name": "Source Reliability and Evidence",
        "description": "Are claims supported with credible references?",
        "weight": 0.15
    }
}

# Critic system prompt for JSON-only output
CRITIC_SYSTEM_PROMPT = """You are a meticulous editor reviewing a draft AI-generated research report. Your goal is to identify specific flaws and provide actionable revisions.

EVALUATION CRITERIA:
1. **Comprehensiveness**: Does the report fully address all initial sub-questions?
2. **Synthesis & Depth**: Does the report merely list facts, or does it synthesize them into a coherent narrative?
3. **Clarity & Coherence**: Is it well-structured, readable, logically organized for the target audience?
4. **Source Reliability**: Are claims supported with credible references?

RESPONSE FORMAT:
You MUST respond ONLY with a valid JSON object in this exact format:
{
  "is_publishable": boolean,
  "revisions_needed": ["Specific revision instruction 1.", "Specific revision instruction 2."]
}

DO NOT include any text before or after the JSON. ONLY return the JSON object."""

# Critic user prompt template
CRITIC_USER_RUBRIC_TEMPLATE = """Please review this draft report against our quality rubric.

**Research Topic**: {topic}
**Target Audience**: {target_audience}

**Sub-Questions to Address**:
{list_of_sub_questions}

**Draft Report**:
---
{draft_report_content}
---

Evaluate the report against these criteria:
1. **Comprehensiveness**: Does the report fully address all initial sub-questions?
2. **Synthesis & Depth**: Does the report merely list facts, or does it synthesize them into a coherent narrative?
3. **Clarity & Coherence**: Is it well-structured, readable, logically organized for the target audience?
4. **Source Reliability**: Are claims supported with credible references?

Provide your evaluation. If it's not publishable, list the necessary revisions."""

# Judge system prompt for JSON-only scoring
JUDGE_SYSTEM_PROMPT = """You are an expert evaluator assessing the quality of research reports using a standardized rubric.

EVALUATION CRITERIA:
1. **Comprehensiveness** (0.0-1.0): Does the report address the initial sub-questions?
2. **Synthesis & Depth** (0.0-1.0): Does it integrate facts into a coherent narrative vs. listing?
3. **Clarity & Coherence** (0.0-1.0): Is it well-structured and readable for the target audience?

RESPONSE FORMAT:
You MUST respond ONLY with a valid JSON object in this exact format:
{
  "comprehensiveness_score": 0.0-1.0,
  "synthesis_score": 0.0-1.0,
  "clarity_score": 0.0-1.0,
  "overall_quality_score": 0.0-1.0,
  "justification": "brief rationale for scores"
}

DO NOT include any text before or after the JSON. ONLY return the JSON object."""

# Judge user prompt template
JUDGE_USER_RUBRIC_TEMPLATE = """Please evaluate this final research report using our quality rubric.

**Sub-Questions that should be addressed**:
{list_of_sub_questions}

**Final Report**:
---
{final_report_content}
---

Evaluate the report on these criteria (score 0.0-1.0 for each):

1. **Comprehensiveness**: Does the report address the initial sub-questions comprehensively?
2. **Synthesis & Depth**: Does it integrate facts into a coherent, insight-rich narrative rather than just listing information?
3. **Clarity & Coherence**: Is it well-structured, readable, and logically organized for the intended audience?

Provide scores and brief justification."""

# Helper functions for prompt assembly
def get_critic_prompts():
    """Get critic prompt fragments for consistent evaluation."""
    return {
        "system_prompt": CRITIC_SYSTEM_PROMPT,
        "user_template": CRITIC_USER_RUBRIC_TEMPLATE
    }

def get_judge_prompts():
    """Get judge prompt fragments for consistent evaluation."""
    return {
        "system_prompt": JUDGE_SYSTEM_PROMPT,
        "user_template": JUDGE_USER_RUBRIC_TEMPLATE
    }

def format_critic_prompt(topic: str, target_audience: str, sub_questions: list, draft_report: str) -> str:
    """Format the critic user prompt with provided data."""
    sub_questions_text = "\n".join(f"- {q}" for q in sub_questions)
    
    return CRITIC_USER_RUBRIC_TEMPLATE.format(
        topic=topic,
        target_audience=target_audience,
        list_of_sub_questions=sub_questions_text,
        draft_report_content=draft_report
    )

def format_judge_prompt(sub_questions: list, final_report: str) -> str:
    """Format the judge user prompt with provided data."""
    sub_questions_text = "\n".join(f"- {q}" for q in sub_questions)
    
    return JUDGE_USER_RUBRIC_TEMPLATE.format(
        list_of_sub_questions=sub_questions_text,
        final_report_content=final_report
    )

def calculate_overall_score(comprehensiveness: float, synthesis: float, clarity: float) -> float:
    """Calculate weighted overall quality score."""
    weights = QUALITY_CRITERIA
    
    total_score = (
        comprehensiveness * weights["comprehensiveness"]["weight"] +
        synthesis * weights["synthesis"]["weight"] +
        clarity * weights["clarity"]["weight"]
    )
    
    # Normalize to account for evidence weight not being used in basic scoring
    normalization_factor = (
        weights["comprehensiveness"]["weight"] +
        weights["synthesis"]["weight"] +
        weights["clarity"]["weight"]
    )
    
    return total_score / normalization_factor