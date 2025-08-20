"""
LLM-as-Judge evaluation module for Nova Brief.

This module implements semantic quality scoring using the same rubric as the Critic
to ensure alignment between generation optimization and evaluation metrics.
"""

import json
import sys
import os
from typing import Dict, Any, List, Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.providers.openrouter_client import LLMClient
from src.observability.logging import get_logger
from src.config import Config

# Import rubric
from .rubric import get_judge_prompts, format_judge_prompt, calculate_overall_score

logger = get_logger(__name__)


async def score_report(
    report_markdown: str,
    sub_questions: List[str],
    model_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Score a research report using LLM-as-Judge evaluation.
    
    Args:
        report_markdown: The final report content in markdown format
        sub_questions: List of sub-questions that should be addressed
        model_key: Optional model key override for evaluation
    
    Returns:
        Dictionary with:
        - comprehensiveness_score: float (0.0-1.0)
        - synthesis_score: float (0.0-1.0) 
        - clarity_score: float (0.0-1.0)
        - overall_quality_score: float (weighted average)
        - justification: brief rationale
        - success: bool
        - error: str (if failed)
    """
    try:
        logger.info("Starting LLM-as-Judge report evaluation")
        
        # Get judge prompts from rubric
        judge_prompts = get_judge_prompts()
        
        # Format the user prompt
        user_prompt = format_judge_prompt(
            sub_questions=sub_questions,
            final_report=report_markdown
        )
        
        # Prepare messages for LLM
        messages = [
            {"role": "system", "content": judge_prompts["system_prompt"]},
            {"role": "user", "content": user_prompt}
        ]
        
        # Determine model to use
        if not model_key:
            # Use default model configuration for judge
            research_mode_name = Config.SELECTED_RESEARCH_MODE
            research_mode_config = Config.get_research_mode_config(research_mode_name)
            model_preference = research_mode_config.get("model_preference", "balanced") if research_mode_config else "balanced"
            model_key = Config.get_agent_model("critic", model_preference, "General")  # Reuse critic model config
        
        # Call LLM for evaluation using LLMClient with model_key
        if model_key:
            client = LLMClient(model_key=model_key)
        else:
            client = LLMClient()  # Use default configuration
            
        response = await client.chat(
            messages=messages,
            temperature=0.1,  # Low temperature for consistent evaluation
            max_tokens=800
        )
        
        if not response["success"]:
            logger.error(f"Judge LLM call failed: {response.get('error')}")
            return _create_fallback_scores(f"LLM call failed: {response.get('error')}")
        
        # Parse JSON response with robust error handling
        content = response.get("content", "")
        
        if not content:
            logger.error("Empty response from judge LLM")
            return _create_fallback_scores("Empty response from LLM")
        
        try:
            # Try direct JSON parsing first
            result = json.loads(content)
        except json.JSONDecodeError:
            # Fallback: Extract JSON from text using regex
            import re
            json_patterns = [
                r'\{.*\}',  # Basic JSON pattern
                r'```json\s*(\{.*?\})\s*```',  # JSON in code blocks
                r'```\s*(\{.*?\})\s*```',  # Generic code blocks
            ]
            
            result = None
            for pattern in json_patterns:
                json_match = re.search(pattern, content, re.DOTALL)
                if json_match:
                    try:
                        json_content = json_match.group(1) if len(json_match.groups()) > 0 else json_match.group(0)
                        result = json.loads(json_content)
                        break
                    except json.JSONDecodeError:
                        continue
            
            if not result:
                logger.warning("Failed to parse judge JSON response, using fallback")
                return _create_fallback_scores("JSON parsing failed")
        
        # Extract and validate scores
        comprehensiveness_score = _validate_score(result.get("comprehensiveness_score", 0.6))
        synthesis_score = _validate_score(result.get("synthesis_score", 0.6))
        clarity_score = _validate_score(result.get("clarity_score", 0.6))
        justification = result.get("justification", "No justification provided")
        
        # Calculate overall score using rubric weights
        overall_score = calculate_overall_score(comprehensiveness_score, synthesis_score, clarity_score)
        
        # Override overall score if provided and valid
        if "overall_quality_score" in result:
            provided_overall = _validate_score(result["overall_quality_score"])
            if provided_overall is not None:
                overall_score = provided_overall
        
        logger.info(f"Judge evaluation completed: overall={overall_score:.3f}, "
                   f"comp={comprehensiveness_score:.3f}, synth={synthesis_score:.3f}, clarity={clarity_score:.3f}")
        
        return {
            "success": True,
            "comprehensiveness_score": comprehensiveness_score,
            "synthesis_score": synthesis_score,
            "clarity_score": clarity_score,
            "overall_quality_score": overall_score,
            "justification": justification,
            "model_used": model_key or "default",
            "sub_questions_count": len(sub_questions),
            "report_length": len(report_markdown)
        }
        
    except Exception as e:
        logger.error(f"Judge evaluation failed: {str(e)}")
        return _create_fallback_scores(f"Evaluation exception: {str(e)}")


def _validate_score(score: Any) -> float:
    """Validate and normalize a score to 0.0-1.0 range."""
    try:
        if score is None:
            return 0.6  # Default fallback
        
        score_float = float(score)
        
        # Clamp to valid range
        return max(0.0, min(1.0, score_float))
        
    except (ValueError, TypeError):
        return 0.6  # Default fallback


def _create_fallback_scores(error_message: str) -> Dict[str, Any]:
    """Create fallback scores when evaluation fails."""
    return {
        "success": False,
        "error": error_message,
        "comprehensiveness_score": 0.6,
        "synthesis_score": 0.6,
        "clarity_score": 0.6,
        "overall_quality_score": 0.6,
        "justification": f"Fallback scores due to evaluation failure: {error_message}",
        "model_used": "fallback",
        "sub_questions_count": 0,
        "report_length": 0
    }


async def batch_score_reports(
    reports: List[Dict[str, Any]],
    model_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Score multiple reports in batch for efficiency.
    
    Args:
        reports: List of report dictionaries with 'report_md' and 'sub_questions' keys
        model_key: Optional model key override
    
    Returns:
        List of scoring results in same order as input
    """
    results = []
    
    for i, report_data in enumerate(reports):
        logger.info(f"Scoring report {i+1}/{len(reports)}")
        
        report_md = report_data.get("report_md", "")
        sub_questions = report_data.get("sub_questions", [])
        
        if not report_md:
            results.append(_create_fallback_scores("Empty report content"))
            continue
        
        score_result = await score_report(
            report_markdown=report_md,
            sub_questions=sub_questions,
            model_key=model_key
        )
        
        results.append(score_result)
    
    return results


def aggregate_scores(score_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate scores across multiple evaluations.
    
    Args:
        score_results: List of score dictionaries from score_report()
    
    Returns:
        Aggregated statistics
    """
    if not score_results:
        return {
            "count": 0,
            "success_rate": 0.0,
            "mean_scores": {},
            "std_scores": {}
        }
    
    successful_results = [r for r in score_results if r.get("success", False)]
    success_rate = len(successful_results) / len(score_results)
    
    if not successful_results:
        return {
            "count": len(score_results),
            "success_rate": success_rate,
            "mean_scores": {},
            "std_scores": {}
        }
    
    # Calculate means
    score_keys = ["comprehensiveness_score", "synthesis_score", "clarity_score", "overall_quality_score"]
    means = {}
    stds = {}
    
    for key in score_keys:
        scores = [r[key] for r in successful_results if key in r]
        if scores:
            means[key] = sum(scores) / len(scores)
            
            # Calculate standard deviation
            if len(scores) > 1:
                variance = sum((x - means[key]) ** 2 for x in scores) / (len(scores) - 1)
                stds[key] = variance ** 0.5
            else:
                stds[key] = 0.0
        else:
            means[key] = 0.0
            stds[key] = 0.0
    
    return {
        "count": len(score_results),
        "successful_count": len(successful_results),
        "success_rate": success_rate,
        "mean_scores": means,
        "std_scores": stds
    }