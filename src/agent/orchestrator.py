"""Agent orchestrator that coordinates the complete research pipeline."""

import time
from typing import Dict, List, Any, Optional
from ..storage.models import (
    ResearchState, create_initial_state, create_default_constraints,
    Constraints, SearchResult, Document, Chunk, Claim, Citation, Report
)
from . import planner, searcher, reader, analyst, verifier, writer
from ..observability.logging import get_logger
from ..observability.tracing import TimedOperation, emit_event

logger = get_logger(__name__)


async def run_research_pipeline(
    topic: str,
    constraints: Optional[Constraints] = None,
    max_rounds: int = 3
) -> Dict[str, Any]:
    """
    Execute the complete research pipeline.
    
    Args:
        topic: Research topic to investigate
        constraints: Research constraints and configuration
        max_rounds: Maximum rounds of iterative refinement
    
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
            
            logger.info(f"Starting research pipeline for topic: {topic}")
            emit_event("pipeline_started", metadata={"topic": topic, "max_rounds": max_rounds})
            
            # Execute pipeline stages
            pipeline_result = await _execute_pipeline_stages(state)
            
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
            
            return {
                "success": True,
                "state": state,
                "report": final_report,
                "metrics": state["metrics"]
            }
            
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


async def _execute_pipeline_stages(state: ResearchState) -> Dict[str, Any]:
    """Execute all pipeline stages with iterative refinement."""
    
    try:
        max_rounds = state["constraints"]["max_rounds"]
        
        # Stage 1: Planning
        planning_result = await _execute_planning_stage(state)
        if not planning_result["success"]:
            return planning_result
        
        # Iterative research rounds
        for round_num in range(1, max_rounds + 1):
            state["current_round"] = round_num
            logger.info(f"Starting research round {round_num}/{max_rounds}")
            
            # Stage 2: Search
            search_result = await _execute_search_stage(state)
            if not search_result["success"]:
                logger.warning(f"Search failed in round {round_num}: {search_result.get('error')}")
                continue
            
            # Stage 3: Reading
            reading_result = await _execute_reading_stage(state)
            if not reading_result["success"]:
                logger.warning(f"Reading failed in round {round_num}: {reading_result.get('error')}")
                continue
            
            # Stage 4: Analysis
            analysis_result = await _execute_analysis_stage(state)
            if not analysis_result["success"]:
                logger.warning(f"Analysis failed in round {round_num}: {analysis_result.get('error')}")
                continue
            
            # Stage 5: Verification
            verification_result = await _execute_verification_stage(state)
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
        
        # Stage 6: Writing (final stage)
        writing_result = await _execute_writing_stage(state)
        if not writing_result["success"]:
            return {
                "success": False,
                "error": f"Writing stage failed: {writing_result.get('error')}"
            }
        
        return {
            "success": True,
            "report": writing_result["report"]
        }
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


async def _execute_planning_stage(state: ResearchState) -> Dict[str, Any]:
    """Execute planning stage."""
    try:
        state["status"] = "planning"
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


async def _execute_search_stage(state: ResearchState) -> Dict[str, Any]:
    """Execute search stage."""
    try:
        state["status"] = "searching"
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


async def _execute_reading_stage(state: ResearchState) -> Dict[str, Any]:
    """Execute reading stage."""
    try:
        state["status"] = "reading"
        emit_event("stage_started", metadata={"stage": "reading", "urls": len(state["search_results"])})
        
        result = await reader.read(state["search_results"], state["constraints"])
        
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


async def _execute_analysis_stage(state: ResearchState) -> Dict[str, Any]:
    """Execute analysis stage."""
    try:
        state["status"] = "analyzing"
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


async def _execute_verification_stage(state: ResearchState) -> Dict[str, Any]:
    """Execute verification stage."""
    try:
        state["status"] = "verifying"
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


async def _execute_writing_stage(state: ResearchState) -> Dict[str, Any]:
    """Execute writing stage."""
    try:
        state["status"] = "writing"
        emit_event("stage_started", metadata={"stage": "writing", "claims": len(state["claims"])})
        
        # Coverage report will be passed from verification stage if needed
        coverage_report = None
        
        result = await writer.write(
            state["claims"],
            state["citations"],
            state["draft_sections"],
            state["topic"],
            state["sub_questions"],
            coverage_report
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