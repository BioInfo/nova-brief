"""Content quality validation utilities for Stage 1.5."""

import re
from typing import Dict, Any


def validate_content(text: str) -> Dict[str, Any]:
    """
    Validate content quality for the Content Quality Gate.
    
    Args:
        text: Raw text content to validate
        
    Returns:
        Dictionary with validation results:
        {
            "ok": bool,
            "reason": Optional[str],
            "metrics": {
                "word_count": int,
                "unique_word_ratio": float,
                "has_boilerplate": bool,
                "detected_phrases": List[str]
            }
        }
    """
    if not text or not text.strip():
        return {
            "ok": False,
            "reason": "Empty or whitespace-only content",
            "metrics": {
                "word_count": 0,
                "unique_word_ratio": 0.0,
                "has_boilerplate": False,
                "detected_phrases": []
            }
        }
    
    # Clean and tokenize text
    words = text.lower().split()
    word_count = len(words)
    unique_words = set(words)
    unique_word_ratio = len(unique_words) / word_count if word_count > 0 else 0.0
    
    # Check minimum word count
    if word_count <= 100:
        return {
            "ok": False,
            "reason": f"Word count too low: {word_count} (minimum: 100)",
            "metrics": {
                "word_count": word_count,
                "unique_word_ratio": unique_word_ratio,
                "has_boilerplate": False,
                "detected_phrases": []
            }
        }
    
    # Check unique word ratio
    if unique_word_ratio < 0.25:
        return {
            "ok": False,
            "reason": f"Unique word ratio too low: {unique_word_ratio:.2f} (minimum: 0.25)",
            "metrics": {
                "word_count": word_count,
                "unique_word_ratio": unique_word_ratio,
                "has_boilerplate": False,
                "detected_phrases": []
            }
        }
    
    # Check for boilerplate/error phrases (case-insensitive)
    boilerplate_phrases = [
        "enable javascript",
        "access denied",
        "forbidden",
        "captcha",
        "page not found",
        "javascript is disabled",
        "cookies must be enabled",
        "please enable cookies",
        "this page requires javascript",
        "error 403",
        "error 404",
        "error 500",
        "service unavailable",
        "temporarily unavailable",
        "site maintenance"
    ]
    
    text_lower = text.lower()
    detected_phrases = []
    
    for phrase in boilerplate_phrases:
        if phrase in text_lower:
            detected_phrases.append(phrase)
    
    has_boilerplate = len(detected_phrases) > 0
    
    if has_boilerplate:
        return {
            "ok": False,
            "reason": f"Contains boilerplate/error phrases: {', '.join(detected_phrases)}",
            "metrics": {
                "word_count": word_count,
                "unique_word_ratio": unique_word_ratio,
                "has_boilerplate": True,
                "detected_phrases": detected_phrases
            }
        }
    
    # All checks passed
    return {
        "ok": True,
        "reason": None,
        "metrics": {
            "word_count": word_count,
            "unique_word_ratio": unique_word_ratio,
            "has_boilerplate": False,
            "detected_phrases": []
        }
    }


def is_likely_error_page(text: str) -> bool:
    """
    Quick check if content is likely an error page.
    
    Args:
        text: Content to check
        
    Returns:
        True if content appears to be an error page
    """
    validation = validate_content(text)
    return not validation["ok"]


def get_content_summary(text: str) -> str:
    """
    Get a brief summary of content characteristics.
    
    Args:
        text: Content to summarize
        
    Returns:
        Human-readable summary string
    """
    validation = validate_content(text)
    metrics = validation["metrics"]
    
    summary_parts = [
        f"{metrics['word_count']} words",
        f"{metrics['unique_word_ratio']:.1%} unique"
    ]
    
    if metrics["has_boilerplate"]:
        summary_parts.append(f"boilerplate detected: {', '.join(metrics['detected_phrases'][:2])}")
    
    return f"Content: {', '.join(summary_parts)}"