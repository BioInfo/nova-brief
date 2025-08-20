"""Agent orchestrator that coordinates the complete research pipeline."""

import time
from typing import Dict, List, Any, Optional, Callable
from ..storage.models import (
    ResearchState, create_initial_state, create_default_constraints,
    Constraints, SearchResult, Document, Chunk, Claim, Citation, Report
)
from . import planner, searcher, reader, analyst, verifier, writer, critic
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from eval import judge
from ..observability.logging import get_logger
from ..observability.tracing import TimedOperation, emit_event

logger = get_logger(__name__)


async def run_research_pipeline(
    topic: str,
    constraints: Optional[Constraints] = None,
    selected_model: Optional[str] = None,
    max_rounds: int = 3,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Execute the complete research pipeline.
    
    Args:
        topic: Research topic to investigate
        constraints: Research constraints and configuration
        selected_model: Model key for LLM selection
        max_rounds: Maximum rounds of iterative refinement
        progress_callback: Optional callback function called with state updates
    
    Returns:
        Dictionary with final report, state, and metrics
    """
    with TimedOperation("research_pipeline") as timer:
        start_time = time.time()
        
        try:
            # Initialize research state
            if constraints is None:
                constraints = create_default_constraints()
                constraints["max_rounds"] = max_rounds
            
            state = create_initial_state(topic, constraints)
            
            # Add model selection to state
            if selected_model:
                state["selected_model"] = selected_model
            
            logger.info(f"Starting research pipeline for topic: {topic}")
            emit_event("pipeline_started", metadata={
                "topic": topic,
                "max_rounds": max_rounds,
                "selected_model": selected_model
            })
            
            # Execute pipeline stages
            pipeline_result = await _execute_pipeline_stages(state, progress_callback)
            
            if not pipeline_result["success"]:
                return {
                    "success": False,
                    "error": pipeline_result["error"],
                    "state": state,
                    "report": None
                }
            
            # Calculate final metrics
            end_time = time.time()
            duration_s = end_time - start_time
            
            state["metrics"]["duration_s"] = duration_s
            state["status"] = "complete"
            state["progress_percent"] = 1.0  # Stage 1.5: Complete
            
            final_report = pipeline_result.get("report")
            
            logger.info(
                f"Research pipeline completed in {duration_s:.1f}s",
                extra={
                    "topic": topic,
                    "duration_s": duration_s,
                    "final_status": state["status"],
                    "claims_count": len(state["claims"]),
                    "documents_count": len(state["documents"]),
                    "word_count": final_report.get("word_count", 0) if final_report else 0
                }
            )
            
            emit_event(
                "pipeline_completed",
                metadata={
                    "topic": topic,
                    "duration_s": duration_s,
                    "success": True,
                    "final_metrics": state["metrics"]
                }
            )
            
            # Extract quality scores from report metadata for top-level access
            quality_scores = {}
            if final_report and "metadata" in final_report:
                metadata = final_report["metadata"]
                quality_scores = {
                    "overall_quality_score": metadata.get("overall_quality_score"),
                    "comprehensiveness_score": metadata.get("comprehensiveness_score"),
                    "synthesis_score": metadata.get("synthesis_score"),
                    "clarity_score": metadata.get("clarity_score"),
                    "justification": metadata.get("justification")
                }
            
            result = {
                "success": True,
                "state": state,
                "report": final_report,
                "metrics": state["metrics"]
            }
            
            # Add quality scores to top level if available
            if any(v is not None for v in quality_scores.values()):
                result.update(quality_scores)
            
            return result
            
        except Exception as e:
            logger.error(f"Research pipeline failed: {e}")
            emit_event(
                "pipeline_error",
                metadata={
                    "topic": topic,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "state": create_initial_state(topic, constraints or create_default_constraints()),
                "report": None
            }


async def _execute_pipeline_stages(state: ResearchState, progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """Execute all pipeline stages with iterative refinement."""
    
    def _notify_progress():
        """Notify UI of progress updates."""
        if progress_callback:
            try:
                progress_callback(state.copy())
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    try:
        max_rounds = state["constraints"]["max_rounds"]
        
        # Stage 1: Planning
        planning_result = await _execute_planning_stage(state, _notify_progress)
        if not planning_result["success"]:
            return planning_result
        
        # Iterative research rounds
        for round_num in range(1, max_rounds + 1):
            state["current_round"] = round_num
            logger.info(f"Starting research round {round_num}/{max_rounds}")
            
            # Stage 2: Search
            search_result = await _execute_search_stage(state, _notify_progress)
            if not search_result["success"]:
                logger.warning(f"Search failed in round {round_num}: {search_result.get('error')}")
                continue
            
            # Stage 3: Reading
            reading_result = await _execute_reading_stage(state, _notify_progress)
            if not reading_result["success"]:
                logger.warning(f"Reading failed in round {round_num}: {reading_result.get('error')}")
                continue
            
            # Stage 4: Analysis
            analysis_result = await _execute_analysis_stage(state, _notify_progress)
            if not analysis_result["success"]:
                logger.warning(f"Analysis failed in round {round_num}: {analysis_result.get('error')}")
                continue
            
            # Stage 5: Verification
            verification_result = await _execute_verification_stage(state, _notify_progress)
            if not verification_result["success"]:
                logger.warning(f"Verification failed in round {round_num}: {verification_result.get('error')}")
                continue
            
            # Check if we need another round
            coverage_report = verification_result.get("coverage_report", {})
            needs_follow_up = verification_result.get("needs_follow_up", False)
            
            if not needs_follow_up or coverage_report.get("coverage_percentage", 0) >= 80:
                logger.info(f"Sufficient coverage achieved in round {round_num}")
                break
            
            # Prepare follow-up queries for next round
            follow_up_queries = verification_result.get("follow_up_queries", [])
            if follow_up_queries and round_num < max_rounds:
                state["queries"].extend(follow_up_queries[:3])  # Add top 3 follow-up queries
                logger.info(f"Added {len(follow_up_queries[:3])} follow-up queries for round {round_num + 1}")
        
        # Stage 6: Writing (draft stage)
        writing_result = await _execute_writing_stage(state, _notify_progress)
        if not writing_result["success"]:
            return {
                "success": False,
                "error": f"Writing stage failed: {writing_result.get('error')}"
            }
        
        # Stage 7: Critic Review Gate (Phase 4 requirement)
        critic_result = await _execute_critic_review_stage(state, writing_result["report"], _notify_progress)
        if not critic_result["success"]:
            # If critic fails, use original report
            logger.warning(f"Critic review failed: {critic_result.get('error')}, using original report")
            return {
                "success": True,
                "report": writing_result["report"]
            }
        
        # Stage 8: Writer Revision (if needed)
        if not critic_result.get("is_publishable", True) and critic_result.get("revisions_needed"):
            revision_result = await _execute_writer_revision_stage(
                state, writing_result["report"], critic_result, _notify_progress
            )
            if revision_result["success"]:
                final_report = revision_result["report"]
            else:
                logger.warning("Writer revision failed, using original report")
                final_report = writing_result["report"]
        else:
            final_report = writing_result["report"]
        
        # Stage 9: LLM-as-Judge Quality Evaluation (Phase 4)
        judge_result = await _execute_judge_evaluation_stage(state, final_report, _notify_progress)
        if judge_result["success"]:
            # Add quality scores to final report metadata
            final_report["metadata"] = final_report.get("metadata", {})
            final_report["metadata"].update(judge_result["quality_scores"])
        
        return {
            "success": True,
            "report": final_report
        }
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


async def _execute_planning_stage(state: ResearchState, notify_progress: Optional[Callable] = None) -> Dict[str, Any]:
    """Execute planning stage."""
    try:
        state["status"] = "planning"
        state["progress_percent"] = 0.1  # Stage 1.5: Planning progress
        if notify_progress:
            notify_progress()
        emit_event("stage_started", metadata={"stage": "planning", "topic": state["topic"]})
        
        result = await planner.plan(state["topic"], state["constraints"])
        
        if result["success"]:
            state["sub_questions"] = result["sub_questions"]
            state["queries"] = result["queries"]
            
            # Update metrics
            state["metrics"]["search_queries"] = len(state["queries"])
            
            logger.info(f"Planning completed: {len(state['sub_questions'])} questions, {len(state['queries'])} queries")
            emit_event("stage_completed", metadata={"stage": "planning", "queries_count": len(state["queries"])})
            
            return {"success": True}
        else:
            return {"success": False, "error": result.get("error")}
            
    except Exception as e:
        logger.error(f"Planning stage failed: {e}")
        return {"success": False, "error": str(e)}


async def _execute_search_stage(state: ResearchState, notify_progress: Optional[Callable] = None) -> Dict[str, Any]:
    """Execute search stage."""
    try:
        state["status"] = "searching"
        state["progress_percent"] = 0.25  # Stage 1.5: Searching progress
        if notify_progress:
            notify_progress()
        emit_event("stage_started", metadata={"stage": "searching", "queries": len(state["queries"])})
        
        result = await searcher.search(state["queries"], state["constraints"])
        
        if result["success"]:
            # Merge with existing search results (for multi-round research)
            new_results = result["search_results"]
            existing_urls = {r["url"] for r in state["search_results"]}
            
            for new_result in new_results:
                if new_result["url"] not in existing_urls:
                    state["search_results"].append(new_result)
            
            logger.info(f"Search completed: {len(new_results)} new results, {len(state['search_results'])} total")
            emit_event("stage_completed", metadata={"stage": "searching", "results_count": len(new_results)})
            
            return {"success": True}
        else:
            return {"success": False, "error": result.get("error")}
            
    except Exception as e:
        logger.error(f"Search stage failed: {e}")
        return {"success": False, "error": str(e)}


async def _execute_reading_stage(state: ResearchState, notify_progress: Optional[Callable] = None) -> Dict[str, Any]:
    """Execute reading stage."""
    try:
        state["status"] = "reading"
        state["progress_percent"] = 0.5  # Stage 1.5: Reading progress
        if notify_progress:
            notify_progress()
        emit_event("stage_started", metadata={"stage": "reading", "urls": len(state["search_results"])})
        
        # Stage 1.5: Pass state to reader for partial failures tracking
        result = await reader.read(state["search_results"], state["constraints"], state)
        
        if result["success"]:
            # Merge with existing documents and chunks
            new_documents = result["documents"]
            new_chunks = result["chunks"]
            
            existing_doc_urls = {d["url"] for d in state["documents"]}
            
            for doc in new_documents:
                if doc["url"] not in existing_doc_urls:
                    state["documents"].append(doc)
            
            state["chunks"].extend(new_chunks)
            
            # Update metrics
            state["metrics"]["urls_fetched"] += result["metadata"].get("successful_fetches", 0)
            state["metrics"]["urls_failed"] += result["metadata"].get("failed_fetches", 0)
            
            logger.info(f"Reading completed: {len(new_documents)} documents, {len(new_chunks)} chunks")
            emit_event("stage_completed", metadata={"stage": "reading", "documents_count": len(new_documents)})
            
            return {"success": True}
        else:
            return {"success": False, "error": result.get("error")}
            
    except Exception as e:
        logger.error(f"Reading stage failed: {e}")
        return {"success": False, "error": str(e)}


async def _execute_analysis_stage(state: ResearchState, notify_progress: Optional[Callable] = None) -> Dict[str, Any]:
    """Execute analysis stage."""
    try:
        state["status"] = "analyzing"
        state["progress_percent"] = 0.7  # Stage 1.5: Analyzing progress
        if notify_progress:
            notify_progress()
        emit_event("stage_started", metadata={"stage": "analyzing", "chunks": len(state["chunks"])})
        
        result = await analyst.analyze(
            state["documents"],
            state["chunks"],
            state["sub_questions"],
            state["topic"]
        )
        
        if result["success"]:
            # Merge with existing claims and citations
            new_claims = result["claims"]
            new_citations = result["citations"]
            
            # Avoid duplicate claims
            existing_claim_texts = {c["text"].lower() for c in state["claims"]}
            
            for claim in new_claims:
                if claim["text"].lower() not in existing_claim_texts:
                    state["claims"].append(claim)
            
            state["citations"].extend(new_citations)
            state["draft_sections"] = result["draft_sections"]
            
            logger.info(f"Analysis completed: {len(new_claims)} new claims, {len(state['claims'])} total")
            emit_event("stage_completed", metadata={"stage": "analyzing", "claims_count": len(new_claims)})
            
            return {"success": True}
        else:
            return {"success": False, "error": result.get("error")}
            
    except Exception as e:
        logger.error(f"Analysis stage failed: {e}")
        return {"success": False, "error": str(e)}


async def _execute_verification_stage(state: ResearchState, notify_progress: Optional[Callable] = None) -> Dict[str, Any]:
    """Execute verification stage."""
    try:
        state["status"] = "verifying"
        state["progress_percent"] = 0.85  # Stage 1.5: Verifying progress
        if notify_progress:
            notify_progress()
        emit_event("stage_started", metadata={"stage": "verifying", "claims": len(state["claims"])})
        
        result = await verifier.verify(
            state["claims"],
            state["citations"],
            state["documents"],
            state["constraints"]
        )
        
        if result["success"]:
            # Update citations with verification results
            state["citations"] = result["updated_citations"]
            
            coverage_report = result["coverage_report"]
            
            logger.info(
                f"Verification completed: {coverage_report['coverage_percentage']:.1f}% coverage",
                extra=coverage_report
            )
            emit_event("stage_completed", metadata={"stage": "verifying", **coverage_report})
            
            return result
        else:
            return {"success": False, "error": result.get("error")}
            
    except Exception as e:
        logger.error(f"Verification stage failed: {e}")
        return {"success": False, "error": str(e)}


async def _execute_writing_stage(state: ResearchState, notify_progress: Optional[Callable] = None) -> Dict[str, Any]:
    """Execute writing stage."""
    try:
        state["status"] = "writing"
        state["progress_percent"] = 0.90  # Adjusted for critic stage
        if notify_progress:
            notify_progress()
        emit_event("stage_started", metadata={"stage": "writing", "claims": len(state["claims"])})
        
        # Coverage report will be passed from verification stage if needed
        coverage_report = None
        
        # Get target audience from state if available
        target_audience = state.get("target_audience", "General")
        
        result = await writer.write(
            state["claims"],
            state["citations"],
            state["draft_sections"],
            state["topic"],
            state["sub_questions"],
            coverage_report,
            target_audience
        )
        
        if result["success"]:
            state["final_report"] = result["report"]
            
            # Update final metrics
            if result["metadata"]:
                state["metrics"]["tokens_out"] += result["metadata"].get("word_count", 0)
                state["metrics"]["sources_count"] = len(state["documents"])
                state["metrics"]["domain_diversity"] = len(set(
                    doc["source_meta"]["domain"] for doc in state["documents"]
                    if "source_meta" in doc and "domain" in doc["source_meta"]
                ))
            
            logger.info(f"Writing completed: {result['metadata']['word_count']} words")
            emit_event("stage_completed", metadata={"stage": "writing", **result["metadata"]})
            
            return result
        else:
            return {"success": False, "error": result.get("error")}
            
    except Exception as e:
        logger.error(f"Writing stage failed: {e}")
        return {"success": False, "error": str(e)}


async def _execute_critic_review_stage(state: ResearchState, draft_report: Dict[str, Any], notify_progress: Optional[Callable] = None) -> Dict[str, Any]:
    """Execute critic review gate stage (Phase 4)."""
    try:
        state["status"] = "reviewing"
        state["progress_percent"] = 0.96
        if notify_progress:
            notify_progress()
        emit_event("stage_started", metadata={"stage": "critic_review", "report_words": draft_report.get("word_count", 0)})
        
        # Get target audience from state
        target_audience = state.get("target_audience", "General")
        
        # Use new review function for gating
        result = await critic.review(
            draft_report=draft_report["report_md"],
            state=dict(state),  # Convert ResearchState to dict
            target_audience=target_audience
        )
        
        if result["success"]:
            is_publishable = result.get("is_publishable", True)
            revisions_count = len(result.get("revisions_needed", []))
            
            logger.info(f"Critic review completed: publishable={is_publishable}, revisions={revisions_count}")
            emit_event("stage_completed", metadata={
                "stage": "critic_review",
                "is_publishable": is_publishable,
                "revisions_count": revisions_count
            })
            
            return result
        else:
            return {"success": False, "error": result.get("error")}
            
    except Exception as e:
        logger.error(f"Critic review stage failed: {e}")
        return {"success": False, "error": str(e)}


async def _execute_writer_revision_stage(
    state: ResearchState,
    original_report: Dict[str, Any],
    critic_review_result: Dict[str, Any],
    notify_progress: Optional[Callable] = None
) -> Dict[str, Any]:
    """Execute writer revision stage based on critic review feedback (Phase 4)."""
    try:
        state["status"] = "revising"
        state["progress_percent"] = 0.98
        if notify_progress:
            notify_progress()
        
        revisions_needed = critic_review_result.get("revisions_needed", [])
        emit_event("stage_started", metadata={"stage": "writer_revision", "revisions_count": len(revisions_needed)})
        
        # Get target audience from state
        target_audience = state.get("target_audience", "General")
        
        logger.info("Creating revised report based on critic review feedback")
        
        # Create revision context from critic feedback
        revision_context = _format_critic_revisions_for_writer(revisions_needed)
        
        # Add revision context to coverage report for writer
        enhanced_coverage_report = {
            "revision_context": revision_context,
            "original_report": original_report["report_md"],
            "critic_feedback": critic_review_result
        }
        
        result = await writer.write(
            state["claims"],
            state["citations"],
            state["draft_sections"],
            state["topic"],
            state["sub_questions"],
            coverage_report=enhanced_coverage_report,
            target_audience=target_audience
        )
        
        if result["success"]:
            # Update final report in state
            state["final_report"] = result["report"]
            
            logger.info(f"Writer revision completed: {result['report']['word_count']} words")
            emit_event("stage_completed", metadata={"stage": "writer_revision", **result["metadata"]})
            
            return result
        else:
            return {"success": False, "error": result.get("error")}
            
    except Exception as e:
        logger.error(f"Writer revision stage failed: {e}")
        return {"success": False, "error": str(e)}


# Utility functions for pipeline management
def get_pipeline_status(state: ResearchState) -> Dict[str, Any]:
    """Get current pipeline status and progress."""
    return {
        "status": state["status"],
        "current_round": state["current_round"],
        "max_rounds": state["constraints"]["max_rounds"],
        "progress": {
            "queries_generated": len(state["queries"]),
            "search_results": len(state["search_results"]),
            "documents_processed": len(state["documents"]),
            "claims_extracted": len(state["claims"]),
            "citations_created": len(state["citations"])
        },
        "metrics": state["metrics"]
    }


def validate_pipeline_inputs(topic: str, constraints: Optional[Constraints] = None) -> Dict[str, Any]:
    """Validate inputs before starting pipeline."""
    issues = []
    
    if not topic or not topic.strip():
        issues.append("Topic is required and cannot be empty")
    
    if topic and len(topic.strip()) < 10:
        issues.append("Topic should be at least 10 characters for meaningful research")
    
    if constraints:
        if constraints.get("max_rounds", 0) < 1:
            issues.append("max_rounds must be at least 1")
        
        if constraints.get("per_domain_cap", 0) < 1:
            issues.append("per_domain_cap must be at least 1")
        
        if constraints.get("fetch_timeout_s", 0) < 5:
            issues.append("fetch_timeout_s should be at least 5 seconds")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues
    }


def _format_critic_feedback_for_revision(critic_feedback: Dict[str, Any]) -> str:
    """Format critic feedback for writer revision instructions."""
    try:
        if not critic_feedback or not isinstance(critic_feedback, dict):
            return "General improvements suggested by critic review."
        
        # Extract critique data
        critique = critic_feedback.get("critique", {})
        if not critique:
            return "General improvements suggested by critic review."
        
        feedback_parts = []
        
        # Overall score and recommendations
        overall_score = critique.get("overall_score", 0)
        if overall_score:
            feedback_parts.append(f"Overall quality score: {overall_score}/10")
        
        # Priority improvements
        priority_improvements = critique.get("priority_improvements", [])
        if priority_improvements:
            feedback_parts.append("\nPriority Improvements:")
            for improvement in priority_improvements[:5]:  # Top 5 improvements
                category = improvement.get("category", "general")
                description = improvement.get("description", "")
                priority = improvement.get("priority", "medium")
                if description:
                    feedback_parts.append(f"- [{priority.upper()}] {category}: {description}")
        
        # Content quality feedback
        content_quality = critique.get("content_quality", {})
        if content_quality:
            issues = content_quality.get("issues", [])
            suggestions = content_quality.get("suggestions", [])
            
            if issues:
                feedback_parts.append(f"\nContent Issues to Address:")
                for issue in issues[:3]:  # Top 3 issues
                    feedback_parts.append(f"- {issue}")
            
            if suggestions:
                feedback_parts.append(f"\nContent Suggestions:")
                for suggestion in suggestions[:3]:  # Top 3 suggestions
                    feedback_parts.append(f"- {suggestion}")
        
        # Structure and clarity feedback
        structure_clarity = critique.get("structure_clarity", {})
        if structure_clarity:
            improvements = structure_clarity.get("improvements", [])
            if improvements:
                feedback_parts.append(f"\nStructural Improvements:")
                for improvement in improvements[:3]:
                    feedback_parts.append(f"- {improvement}")
        
        # Evidence support feedback
        evidence_support = critique.get("evidence_support", {})
        if evidence_support:
            weak_support = evidence_support.get("weak_support", [])
            unsupported = evidence_support.get("unsupported", [])
            
            if weak_support or unsupported:
                feedback_parts.append(f"\nEvidence Improvements:")
                for claim in weak_support[:2]:
                    feedback_parts.append(f"- Strengthen evidence for: {claim}")
                for claim in unsupported[:2]:
                    feedback_parts.append(f"- Add sources for: {claim}")
        
        # Bias and completeness feedback
        bias_objectivity = critique.get("bias_objectivity", {})
        if bias_objectivity:
            missing_perspectives = bias_objectivity.get("missing_perspectives", [])
            if missing_perspectives:
                feedback_parts.append(f"\nPerspectives to Include:")
                for perspective in missing_perspectives[:3]:
                    feedback_parts.append(f"- {perspective}")
        
        completeness = critique.get("completeness", {})
        if completeness:
            gaps = completeness.get("gaps", [])
            if gaps:
                feedback_parts.append(f"\nContent Gaps to Fill:")
                for gap in gaps[:3]:
                    feedback_parts.append(f"- {gap}")
        
        if feedback_parts:
            return "\n".join(feedback_parts)
        else:
            return "General improvements suggested by critic review."
    
    except Exception as e:
        logger.warning(f"Error formatting critic feedback: {e}")
        return "General improvements suggested by critic review."


async def _execute_judge_evaluation_stage(state: ResearchState, final_report: Dict[str, Any], notify_progress: Optional[Callable] = None) -> Dict[str, Any]:
    """Execute LLM-as-Judge quality evaluation stage (Phase 4)."""
    try:
        state["status"] = "evaluating"
        state["progress_percent"] = 0.99
        if notify_progress:
            notify_progress()
        emit_event("stage_started", metadata={"stage": "judge_evaluation", "report_words": final_report.get("word_count", 0)})
        
        # Extract report content for evaluation
        report_content = final_report.get("report_md", "")
        if not report_content:
            logger.warning("No report content available for judge evaluation")
            return {"success": False, "error": "No report content available"}
        
        # Use judge evaluation
        result = await judge.score_report(
            report_markdown=report_content,
            sub_questions=state.get("sub_questions", [])
        )
        
        if result["success"]:
            quality_scores = {
                "overall_quality_score": result.get("overall_quality_score", 0.6),
                "comprehensiveness_score": result.get("comprehensiveness_score", 0.6),
                "synthesis_score": result.get("synthesis_score", 0.6),
                "clarity_score": result.get("clarity_score", 0.6),
                "justification": result.get("justification", "LLM-as-Judge evaluation completed"),
                "judge_model_used": result.get("model_used", "default")
            }
            
            logger.info(f"Judge evaluation completed: overall={quality_scores['overall_quality_score']:.3f}")
            emit_event("stage_completed", metadata={
                "stage": "judge_evaluation",
                "overall_quality_score": quality_scores["overall_quality_score"]
            })
            
            return {
                "success": True,
                "quality_scores": quality_scores
            }
        else:
            logger.warning(f"Judge evaluation failed: {result.get('error')}")
            # Return fallback scores
            fallback_scores = {
                "overall_quality_score": 0.6,
                "comprehensiveness_score": 0.6,
                "synthesis_score": 0.6,
                "clarity_score": 0.6,
                "justification": f"Judge evaluation failed: {result.get('error', 'Unknown error')}",
                "judge_model_used": "fallback"
            }
            return {
                "success": True,  # Don't fail the pipeline for judge issues
                "quality_scores": fallback_scores
            }
            
    except Exception as e:
        logger.error(f"Judge evaluation stage failed: {e}")
        # Return fallback scores on exception
        fallback_scores = {
            "overall_quality_score": 0.6,
            "comprehensiveness_score": 0.6,
            "synthesis_score": 0.6,
            "clarity_score": 0.6,
            "justification": f"Judge evaluation exception: {str(e)}",
            "judge_model_used": "fallback"
        }
        return {
            "success": True,  # Don't fail the pipeline for judge issues
            "quality_scores": fallback_scores
        }


def _format_critic_revisions_for_writer(revisions_needed: List[str]) -> str:
    """Format critic revisions for writer revision instructions (Phase 4)."""
    try:
        if not revisions_needed:
            return "No specific revisions requested by critic review."
        
        revision_parts = [
            "REVISION INSTRUCTIONS:",
            "The critic has identified the following areas for improvement:",
            ""
        ]
        
        for i, revision in enumerate(revisions_needed, 1):
            revision_parts.append(f"{i}. {revision}")
        
        revision_parts.extend([
            "",
            "Please incorporate these specific improvements into a revised version of the report.",
            "Focus on addressing each point while maintaining the overall structure and flow."
        ])
        
        return "\n".join(revision_parts)
        
    except Exception as e:
        logger.warning(f"Error formatting critic revisions: {e}")
        return "General improvements requested by critic review."