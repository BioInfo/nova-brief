"""ETA (Estimated Time of Arrival) calculation utilities for Stage 1.5."""

import json
import glob
import os
from typing import Optional, Dict, Any, List
from datetime import datetime


def get_latest_eval_results(eval_dir: str = "eval") -> Optional[Dict[str, Any]]:
    """
    Get the most recent evaluation results file.
    
    Args:
        eval_dir: Directory containing evaluation results
        
    Returns:
        Dictionary with evaluation results or None if not found
    """
    try:
        # Find all results files
        pattern = os.path.join(eval_dir, "results_*.json")
        result_files = glob.glob(pattern)
        
        if not result_files:
            return None
        
        # Get the most recent file by modification time
        latest_file = max(result_files, key=os.path.getmtime)
        
        with open(latest_file, 'r') as f:
            return json.load(f)
            
    except Exception:
        return None


def calculate_average_duration(eval_results: Optional[Dict[str, Any]] = None) -> Optional[float]:
    """
    Calculate average duration from evaluation results.
    
    Args:
        eval_results: Evaluation results dictionary
        
    Returns:
        Average duration in seconds or None if not available
    """
    if not eval_results:
        eval_results = get_latest_eval_results()
    
    if not eval_results:
        return None
    
    try:
        # Handle both single result and multi-result formats
        if "duration_s" in eval_results:
            # Single result format
            return float(eval_results["duration_s"])
        elif "results" in eval_results and isinstance(eval_results["results"], list):
            # Multi-result format
            durations = []
            for result in eval_results["results"]:
                if "duration_s" in result:
                    durations.append(float(result["duration_s"]))
            
            if durations:
                return sum(durations) / len(durations)
        elif "topics" in eval_results:
            # Topic-based results format
            durations = []
            for topic_result in eval_results["topics"].values():
                if "duration_s" in topic_result:
                    durations.append(float(topic_result["duration_s"]))
            
            if durations:
                return sum(durations) / len(durations)
                
        return None
        
    except Exception:
        return None


def estimate_eta(progress_percent: float, start_time: Optional[float] = None) -> Optional[float]:
    """
    Estimate time remaining based on progress and historical data.
    
    Args:
        progress_percent: Current progress as a float between 0.0 and 1.0
        start_time: Start time of current operation (time.time())
        
    Returns:
        Estimated seconds remaining or None if cannot calculate
    """
    if progress_percent <= 0 or progress_percent >= 1.0:
        return None
    
    # Get average duration from historical data
    avg_duration = calculate_average_duration()
    
    if avg_duration is None:
        # Fallback: use default estimates if no historical data
        avg_duration = 60.0  # Default 60 seconds estimate
    
    # Calculate ETA based on progress
    remaining_percent = 1.0 - progress_percent
    eta_seconds = avg_duration * remaining_percent
    
    # If we have a start time, we can also use elapsed time for better accuracy
    if start_time:
        import time
        elapsed = time.time() - start_time
        if progress_percent > 0.1:  # Only use after some meaningful progress
            estimated_total = elapsed / progress_percent
            eta_from_elapsed = estimated_total - elapsed
            # Average the two estimates, weighting historical data more heavily early on
            weight_historical = max(0.3, 1.0 - progress_percent)
            eta_seconds = (eta_seconds * weight_historical + 
                          eta_from_elapsed * (1 - weight_historical))
    
    return max(0, eta_seconds)


def format_eta(eta_seconds: Optional[float]) -> str:
    """
    Format ETA in human-readable format.
    
    Args:
        eta_seconds: ETA in seconds
        
    Returns:
        Formatted string like "~2m 30s" or "~45s"
    """
    if eta_seconds is None:
        return ""
    
    eta_seconds = int(eta_seconds)
    
    if eta_seconds < 60:
        return f"~{eta_seconds}s"
    elif eta_seconds < 3600:
        minutes = eta_seconds // 60
        seconds = eta_seconds % 60
        if seconds > 0:
            return f"~{minutes}m {seconds}s"
        else:
            return f"~{minutes}m"
    else:
        hours = eta_seconds // 3600
        minutes = (eta_seconds % 3600) // 60
        return f"~{hours}h {minutes}m"


def get_stage_estimates() -> Dict[str, float]:
    """
    Get rough estimates for each stage as a percentage of total time.
    
    Returns:
        Dictionary mapping stage names to percentage estimates
    """
    return {
        "planning": 0.1,
        "searching": 0.15,
        "reading": 0.25,
        "analyzing": 0.35,
        "verifying": 0.1,
        "writing": 0.05
    }


def estimate_stage_eta(current_stage: str, progress_percent: float) -> Optional[float]:
    """
    Estimate ETA for a specific stage.
    
    Args:
        current_stage: Name of current stage
        progress_percent: Overall progress percentage
        
    Returns:
        Estimated seconds for current stage or None
    """
    stage_estimates = get_stage_estimates()
    avg_duration = calculate_average_duration()
    
    if avg_duration is None or current_stage not in stage_estimates:
        return None
    
    stage_duration = avg_duration * stage_estimates[current_stage]
    
    # Find what percentage of this stage is complete based on overall progress
    stage_start_progress = 0
    for stage, pct in stage_estimates.items():
        if stage == current_stage:
            break
        stage_start_progress += pct
    
    stage_end_progress = stage_start_progress + stage_estimates[current_stage]
    
    if progress_percent <= stage_start_progress:
        # Haven't started this stage yet
        return stage_duration
    elif progress_percent >= stage_end_progress:
        # Stage is complete
        return 0
    else:
        # Partially complete
        stage_progress = (progress_percent - stage_start_progress) / stage_estimates[current_stage]
        return stage_duration * (1 - stage_progress)