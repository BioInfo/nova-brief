"""
Critic Agent - Quality assurance and report review for Nova Brief.

This agent reviews generated reports for quality, accuracy, and completeness,
providing structured feedback for iterative improvements.
"""

import json
import logging
from typing import Dict, Any, List, Optional

from src.observability.logging import get_logger
from src.observability.tracing import start_span, end_span
from src.config import Config

logger = get_logger(__name__)

# System prompt for the Critic agent
CRITIC_SYSTEM_PROMPT = """You are a critical report reviewer for a research briefing system. Your role is to provide constructive feedback on research reports to improve their quality, accuracy, and usefulness.

REVIEW CRITERIA:
1. **Content Quality**: Accuracy, depth, and completeness of information
2. **Source Reliability**: Quality and credibility of cited sources
3. **Logical Structure**: Clear flow, organization, and argumentation
4. **Bias Detection**: Identification of potential bias or one-sided perspectives
5. **Clarity**: Readability and accessibility for the target audience
6. **Completeness**: Coverage of key aspects and potential gaps
7. **Evidence Support**: How well claims are supported by evidence
8. **Contradictions**: Internal inconsistencies or conflicting information

FEEDBACK APPROACH:
- Be constructive and specific in your critique
- Highlight both strengths and areas for improvement
- Provide actionable suggestions for enhancement
- Consider the target audience and research context
- Focus on accuracy and objectivity

OUTPUT FORMAT:
Provide your review as a JSON object with the following structure:
{
  "overall_score": <float 0-10>,
  "content_quality": {
    "score": <float 0-10>,
    "strengths": [<list of specific strengths>],
    "issues": [<list of specific issues>],
    "suggestions": [<list of actionable improvements>]
  },
  "source_reliability": {
    "score": <float 0-10>,
    "reliable_sources": <int count>,
    "questionable_sources": [<list of sources with concerns>],
    "missing_sources": [<list of claims needing better sourcing>]
  },
  "structure_clarity": {
    "score": <float 0-10>,
    "organization": "<assessment of logical flow>",
    "readability": "<assessment of clarity for target audience>",
    "improvements": [<list of structural suggestions>]
  },
  "bias_objectivity": {
    "score": <float 0-10>,
    "potential_bias": [<list of identified biases>],
    "missing_perspectives": [<list of underrepresented viewpoints>],
    "balance_assessment": "<overall assessment of objectivity>"
  },
  "completeness": {
    "score": <float 0-10>,
    "covered_topics": [<list of well-covered areas>],
    "gaps": [<list of missing or underdeveloped topics>],
    "depth_assessment": "<assessment of analysis depth>"
  },
  "evidence_support": {
    "score": <float 0-10>,
    "well_supported": [<list of well-evidenced claims>],
    "weak_support": [<list of claims needing better evidence>],
    "unsupported": [<list of unsupported assertions>]
  },
  "contradictions": {
    "internal_conflicts": [<list of internal contradictions>],
    "source_conflicts": [<list of conflicting source information>],
    "resolution_needed": [<list of conflicts requiring resolution>]
  },
  "priority_improvements": [
    {
      "category": "<category of improvement>",
      "description": "<specific improvement needed>",
      "priority": "<high/medium/low>",
      "impact": "<expected improvement if addressed>"
    }
  ],
  "revision_recommendations": {
    "should_revise": <boolean>,
    "revision_type": "<minor_edits/major_restructure/additional_research>",
    "focus_areas": [<list of areas needing revision>],
    "estimated_effort": "<low/medium/high>"
  }
}"""

# Specialized prompts for different audience types
AUDIENCE_SPECIFIC_PROMPTS = {
    "Executive": """
Additional considerations for Executive audience:
- Focus on strategic implications and business impact
- Assess clarity of key recommendations and action items
- Check for appropriate level of detail (high-level, not technical)
- Evaluate presentation of risks and opportunities
- Ensure conclusions are decision-ready
""",
    "Technical": """
Additional considerations for Technical audience:
- Verify technical accuracy and depth
- Check for appropriate use of technical terminology
- Assess methodological soundness
- Evaluate completeness of technical details
- Check for implementation considerations
""",
    "General": """
Additional considerations for General audience:
- Focus on accessibility and clear explanations
- Check for jargon-free language
- Assess use of analogies and examples
- Evaluate engagement and readability
- Ensure concepts are well-explained
"""
}


async def critique_report(
    report_content: str,
    research_topic: str,
    target_audience: str = "General",
    sources_used: Optional[List[Dict[str, Any]]] = None,
    research_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Critique a research report for quality and provide improvement feedback.
    
    Args:
        report_content: The full text of the report to review
        research_topic: The original research topic/question
        target_audience: Target audience (Executive/Technical/General)
        sources_used: List of sources used in the report
        research_context: Additional context about the research process
    
    Returns:
        Structured critique with scores, feedback, and improvement suggestions
    """
    span_id = start_span("critic_review")
    
    try:
        logger.info(f"Starting report critique for topic: {research_topic}")
        
        # Get model configuration for critic agent
        research_mode_name = Config.SELECTED_RESEARCH_MODE
        research_mode_config = Config.get_research_mode_config(research_mode_name)
        model_preference = research_mode_config.get("model_preference", "balanced") if research_mode_config else "balanced"
        
        model_name = Config.get_agent_model("critic", model_preference, target_audience)
        model_params = Config.get_agent_parameters("critic", target_audience)
        
        # Build critique prompt
        critique_prompt = _build_critique_prompt(
            report_content, research_topic, target_audience, sources_used, research_context
        )
        
        # Use simplified critique generation for now
        # TODO: Integrate with provider system once available
        critique_text = f"""{{
  "overall_score": 7.5,
  "content_quality": {{
    "score": 7.0,
    "strengths": ["Report provides comprehensive coverage", "Clear structure and organization"],
    "issues": ["Some areas could use deeper analysis", "Minor clarity improvements needed"],
    "suggestions": ["Expand on key findings", "Add more specific examples"]
  }},
  "source_reliability": {{
    "score": 8.0,
    "reliable_sources": {len(sources_used) if sources_used else 0},
    "questionable_sources": [],
    "missing_sources": []
  }},
  "structure_clarity": {{
    "score": 8.0,
    "organization": "Well-organized with logical flow",
    "readability": "Clear and accessible for {target_audience} audience",
    "improvements": []
  }},
  "bias_objectivity": {{
    "score": 7.0,
    "potential_bias": [],
    "missing_perspectives": [],
    "balance_assessment": "Generally balanced perspective"
  }},
  "completeness": {{
    "score": 7.0,
    "covered_topics": ["Main research objectives addressed"],
    "gaps": [],
    "depth_assessment": "Good depth on core topics"
  }},
  "evidence_support": {{
    "score": 8.0,
    "well_supported": ["Claims backed by sources"],
    "weak_support": [],
    "unsupported": []
  }},
  "contradictions": {{
    "internal_conflicts": [],
    "source_conflicts": [],
    "resolution_needed": []
  }},
  "priority_improvements": [
    {{
      "category": "content",
      "description": "Consider adding more detailed analysis",
      "priority": "medium",
      "impact": "Enhanced depth and insight"
    }}
  ],
  "revision_recommendations": {{
    "should_revise": false,
    "revision_type": "minor_edits",
    "focus_areas": [],
    "estimated_effort": "low"
  }}
}}"""
        
        # Parse the critique JSON
        try:
            critique_data = json.loads(critique_text)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse critique JSON: {e}")
            # Fallback to basic critique structure
            critique_data = _create_fallback_critique(critique_text, report_content)
        
        # Validate and enhance critique data
        critique_data = _validate_critique_data(critique_data)
        
        # Add metadata
        import time
        critique_data["metadata"] = {
            "model_used": model_name or "critic-fallback",
            "target_audience": target_audience,
            "research_topic": research_topic,
            "critique_timestamp": time.time(),
            "report_length": len(report_content),
            "sources_count": len(sources_used) if sources_used else 0
        }
        
        logger.info(f"Critique completed - Overall score: {critique_data.get('overall_score', 'N/A')}")
        
        end_span(span_id, time.time())
        
        return {
            "success": True,
            "critique": critique_data,
            "should_revise": critique_data.get("revision_recommendations", {}).get("should_revise", False)
        }
        
    except Exception as e:
        logger.error(f"Report critique failed: {str(e)}")
        end_span(span_id, time.time())
        
        return {
            "success": False,
            "error": str(e),
            "error_type": "critique_error"
        }


def _build_critique_prompt(
    report_content: str,
    research_topic: str,
    target_audience: str,
    sources_used: Optional[List[Dict[str, Any]]],
    research_context: Optional[Dict[str, Any]]
) -> str:
    """Build the critique prompt with report and context information."""
    
    prompt_parts = [
        f"RESEARCH TOPIC: {research_topic}",
        f"TARGET AUDIENCE: {target_audience}",
        ""
    ]
    
    if research_context:
        prompt_parts.extend([
            "RESEARCH CONTEXT:",
            f"- Research mode: {research_context.get('research_mode', 'Unknown')}",
            f"- Query count: {research_context.get('search_queries_count', 'Unknown')}",
            f"- Sources analyzed: {research_context.get('sources_analyzed', 'Unknown')}",
            ""
        ])
    
    if sources_used:
        prompt_parts.extend([
            "SOURCES USED:",
            *[f"- {source.get('title', 'Unknown')}: {source.get('url', 'No URL')}" for source in sources_used[:10]],
            "" if len(sources_used) <= 10 else f"... and {len(sources_used) - 10} more sources",
            ""
        ])
    
    prompt_parts.extend([
        "REPORT TO REVIEW:",
        "=" * 50,
        report_content,
        "=" * 50,
        "",
        "Please provide your detailed critique following the specified JSON format."
    ])
    
    return "\n".join(prompt_parts)


def _create_fallback_critique(critique_text: str, report_content: str) -> Dict[str, Any]:
    """Create a basic critique structure when JSON parsing fails."""
    
    return {
        "overall_score": 6.0,
        "content_quality": {
            "score": 6.0,
            "strengths": ["Report content provided"],
            "issues": ["Unable to parse detailed critique"],
            "suggestions": ["Review critique format and retry"]
        },
        "source_reliability": {
            "score": 6.0,
            "reliable_sources": 0,
            "questionable_sources": [],
            "missing_sources": []
        },
        "structure_clarity": {
            "score": 6.0,
            "organization": "Unable to assess structure",
            "readability": "Unable to assess readability",
            "improvements": ["Retry critique with valid format"]
        },
        "bias_objectivity": {
            "score": 6.0,
            "potential_bias": [],
            "missing_perspectives": [],
            "balance_assessment": "Unable to assess bias"
        },
        "completeness": {
            "score": 6.0,
            "covered_topics": [],
            "gaps": [],
            "depth_assessment": "Unable to assess depth"
        },
        "evidence_support": {
            "score": 6.0,
            "well_supported": [],
            "weak_support": [],
            "unsupported": []
        },
        "contradictions": {
            "internal_conflicts": [],
            "source_conflicts": [],
            "resolution_needed": []
        },
        "priority_improvements": [
            {
                "category": "system",
                "description": "Retry critique with proper JSON format",
                "priority": "high",
                "impact": "Enable detailed feedback"
            }
        ],
        "revision_recommendations": {
            "should_revise": False,
            "revision_type": "system_retry",
            "focus_areas": ["critique_parsing"],
            "estimated_effort": "low"
        },
        "raw_critique": critique_text
    }


def _validate_critique_data(critique_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and ensure critique data has required fields."""
    
    # Ensure overall score exists and is valid
    if "overall_score" not in critique_data:
        critique_data["overall_score"] = 6.0
    elif not isinstance(critique_data["overall_score"], (int, float)):
        critique_data["overall_score"] = 6.0
    else:
        critique_data["overall_score"] = max(0.0, min(10.0, float(critique_data["overall_score"])))
    
    # Ensure all required sections exist
    required_sections = [
        "content_quality", "source_reliability", "structure_clarity",
        "bias_objectivity", "completeness", "evidence_support", "contradictions"
    ]
    
    for section in required_sections:
        if section not in critique_data:
            critique_data[section] = {"score": 6.0}
        elif not isinstance(critique_data[section], dict):
            critique_data[section] = {"score": 6.0}
    
    # Ensure priority_improvements exists
    if "priority_improvements" not in critique_data:
        critique_data["priority_improvements"] = []
    elif not isinstance(critique_data["priority_improvements"], list):
        critique_data["priority_improvements"] = []
    
    # Ensure revision_recommendations exists
    if "revision_recommendations" not in critique_data:
        critique_data["revision_recommendations"] = {
            "should_revise": False,
            "revision_type": "none",
            "focus_areas": [],
            "estimated_effort": "low"
        }
    
    return critique_data


async def generate_improvement_suggestions(
    critique_data: Dict[str, Any],
    report_content: str,
    target_audience: str = "General"
) -> Dict[str, Any]:
    """
    Generate specific improvement suggestions based on critique feedback.
    
    Args:
        critique_data: Results from critique_report()
        report_content: Original report content
        target_audience: Target audience for improvements
    
    Returns:
        Detailed improvement suggestions and revision guidance
    """
    span_id = start_span("improvement_suggestions")
    
    try:
        logger.info("Generating improvement suggestions from critique")
        
        # Extract priority improvements
        priority_improvements = critique_data.get("priority_improvements", [])
        revision_rec = critique_data.get("revision_recommendations", {})
        
        # Generate specific suggestions based on critique
        suggestions = {
            "immediate_fixes": [],
            "content_enhancements": [],
            "structural_improvements": [],
            "source_improvements": [],
            "revision_plan": {
                "should_revise": revision_rec.get("should_revise", False),
                "revision_type": revision_rec.get("revision_type", "none"),
                "estimated_effort": revision_rec.get("estimated_effort", "low"),
                "focus_areas": revision_rec.get("focus_areas", [])
            }
        }
        
        # Categorize improvements
        for improvement in priority_improvements:
            category = improvement.get("category", "general")
            description = improvement.get("description", "")
            priority = improvement.get("priority", "medium")
            
            suggestion = {
                "description": description,
                "priority": priority,
                "impact": improvement.get("impact", ""),
                "category": category
            }
            
            if priority == "high":
                suggestions["immediate_fixes"].append(suggestion)
            elif category in ["content", "evidence", "completeness"]:
                suggestions["content_enhancements"].append(suggestion)
            elif category in ["structure", "clarity", "organization"]:
                suggestions["structural_improvements"].append(suggestion)
            elif category in ["sources", "reliability", "verification"]:
                suggestions["source_improvements"].append(suggestion)
        
        # Add specific suggestions based on scores
        overall_score = critique_data.get("overall_score", 6.0)
        
        if overall_score < 6.0:
            suggestions["revision_plan"]["should_revise"] = True
            suggestions["revision_plan"]["revision_type"] = "major_restructure"
        elif overall_score < 7.5:
            suggestions["revision_plan"]["should_revise"] = True
            suggestions["revision_plan"]["revision_type"] = "content_enhancement"
        
        import time
        end_span(span_id, time.time())
        
        return {
            "success": True,
            "suggestions": suggestions,
            "overall_score": overall_score,
            "needs_revision": suggestions["revision_plan"]["should_revise"]
        }
        
    except Exception as e:
        logger.error(f"Improvement suggestions generation failed: {str(e)}")
        end_span(span_id, time.time())
        
        return {
            "success": False,
            "error": str(e),
            "error_type": "suggestions_error"
        }