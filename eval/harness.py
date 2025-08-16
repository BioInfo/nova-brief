"""
Evaluation harness for the Nova Brief research agent.
Runs standardized tests on predefined topics and measures performance metrics.
"""

import asyncio
import json
import time
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add src to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from agent import planner, searcher, reader, analyst, verifier, writer
from observability.logging import get_logger, configure_logging
from observability.tracing import get_trace_events, clear_trace_events

# Configure logging
configure_logging()
logger = get_logger(__name__)


class EvaluationHarness:
    """Evaluation harness for testing research agent performance."""
    
    def __init__(self):
        self.topics_file = Path(__file__).parent / "topics.json"
        self.results_dir = Path(__file__).parent.parent / "exports"
        self.results_dir.mkdir(exist_ok=True)
        
        # Performance thresholds (from PRD)
        self.max_duration_seconds = 360  # 6 minutes
        self.min_sources = 5
        self.min_coverage_score = 0.7
        self.max_dead_link_rate = 0.05
        self.max_duplicate_rate = 0.10
    
    def load_topics(self) -> List[Dict[str, Any]]:
        """Load evaluation topics from JSON file."""
        try:
            with open(self.topics_file, 'r') as f:
                topics = json.load(f)
            logger.info(f"Loaded {len(topics)} evaluation topics")
            return topics
        except Exception as e:
            logger.error(f"Failed to load topics: {e}")
            return []
    
    async def run_single_evaluation(self, topic_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run evaluation on a single topic.
        
        Args:
            topic_data: Topic configuration from topics.json
        
        Returns:
            Evaluation results
        """
        topic_id = topic_data["id"]
        topic = topic_data["topic"]
        
        logger.info(f"Starting evaluation for topic: {topic_id}")
        
        start_time = time.time()
        result = {
            "topic_id": topic_id,
            "topic": topic,
            "start_time": start_time,
            "success": False,
            "error": None,
            "metrics": {},
            "steps": {}
        }
        
        try:
            # Clear trace events
            clear_trace_events()
            
            # Step 1: Planning
            plan_result = await planner.plan(topic)
            result["steps"]["planning"] = plan_result
            
            if not plan_result["success"]:
                raise Exception(f"Planning failed: {plan_result.get('error')}")
            
            # Step 2: Searching
            queries = plan_result["all_queries"]
            search_result = await searcher.search(queries)
            result["steps"]["searching"] = search_result
            
            if not search_result["success"]:
                raise Exception(f"Search failed: {search_result.get('error')}")
            
            # Step 3: Reading
            search_results = search_result["results"]
            read_result = await reader.read(search_results)
            result["steps"]["reading"] = read_result
            
            if not read_result["success"]:
                raise Exception(f"Reading failed: {read_result.get('error')}")
            
            # Step 4: Analysis
            chunks = read_result["chunks"]
            analysis_result = await analyst.analyze(chunks, topic)
            result["steps"]["analysis"] = analysis_result
            
            if not analysis_result["success"]:
                raise Exception(f"Analysis failed: {analysis_result.get('error')}")
            
            # Step 5: Verification
            verification_result = await verifier.verify(analysis_result)
            result["steps"]["verification"] = verification_result
            
            if not verification_result["success"]:
                raise Exception(f"Verification failed: {verification_result.get('error')}")
            
            # Step 6: Writing
            documents = read_result["documents"]
            write_result = await writer.write(verification_result, analysis_result, documents)
            result["steps"]["writing"] = write_result
            
            if not write_result["success"]:
                raise Exception(f"Writing failed: {write_result.get('error')}")
            
            # Calculate end-to-end metrics
            end_time = time.time()
            duration = end_time - start_time
            
            # Extract metrics from steps
            metrics = self._extract_metrics(result["steps"], duration)
            result["metrics"] = metrics
            result["duration"] = duration
            result["success"] = True
            
            # Save report
            report_path = self._save_report(topic_id, write_result["report_markdown"], metrics)
            result["report_path"] = str(report_path)
            
            logger.info(f"Evaluation completed for {topic_id}: {duration:.1f}s")
            
        except Exception as e:
            end_time = time.time()
            result["duration"] = end_time - start_time
            result["error"] = str(e)
            logger.error(f"Evaluation failed for {topic_id}: {e}")
        
        return result
    
    def _extract_metrics(self, steps: Dict[str, Any], duration: float) -> Dict[str, Any]:
        """Extract performance metrics from step results."""
        metrics = {
            "duration_seconds": duration,
            "total_tokens": 0,
            "total_queries": 0,
            "unique_sources": 0,
            "successful_fetches": 0,
            "total_claims": 0,
            "verified_claims": 0,
            "coverage_score": 0,
            "word_count": 0,
            "citation_count": 0,
            "dead_link_rate": 0,
            "duplicate_rate": 0
        }
        
        # Planning metrics
        if "planning" in steps:
            plan_data = steps["planning"]
            metrics["total_queries"] = plan_data.get("query_count", 0)
            if "tokens_used" in plan_data:
                metrics["total_tokens"] += plan_data["tokens_used"]
        
        # Search metrics
        if "searching" in steps:
            search_data = steps["searching"]
            search_metrics = search_data.get("metrics", {})
            metrics["unique_sources"] = search_metrics.get("total_unique_results", 0)
            metrics["duplicate_rate"] = search_metrics.get("deduplication_ratio", 0)
        
        # Reading metrics
        if "reading" in steps:
            read_data = steps["reading"]
            read_metrics = read_data.get("metrics", {})
            metrics["successful_fetches"] = read_metrics.get("successful_fetches", 0)
            total_urls = read_metrics.get("total_urls", 1)
            metrics["dead_link_rate"] = 1 - (metrics["successful_fetches"] / max(total_urls, 1))
        
        # Analysis metrics
        if "analysis" in steps:
            analysis_data = steps["analysis"]
            analysis_metrics = analysis_data.get("metrics", {})
            metrics["total_claims"] = analysis_metrics.get("total_claims", 0)
        
        # Verification metrics
        if "verification" in steps:
            verification_data = steps["verification"]
            verification_metrics = verification_data.get("verification_metrics", {})
            metrics["verified_claims"] = verification_metrics.get("verified_claims", 0)
            metrics["coverage_score"] = verification_metrics.get("coverage_score", 0)
        
        # Writing metrics
        if "writing" in steps:
            write_data = steps["writing"]
            write_metrics = write_data.get("metrics", {})
            metrics["word_count"] = write_metrics.get("word_count", 0)
            metrics["citation_count"] = write_metrics.get("citation_count", 0)
        
        return metrics
    
    def _save_report(self, topic_id: str, report_content: str, metrics: Dict[str, Any]) -> Path:
        """Save evaluation report to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"eval_{topic_id}_{timestamp}.md"
        report_path = self.results_dir / filename
        
        # Add metrics header to report
        metrics_header = f"""---
# Evaluation Metrics for {topic_id}
- Duration: {metrics.get('duration_seconds', 0):.1f}s
- Sources: {metrics.get('unique_sources', 0)}
- Claims: {metrics.get('total_claims', 0)} ({metrics.get('verified_claims', 0)} verified)
- Coverage Score: {metrics.get('coverage_score', 0):.1%}
- Word Count: {metrics.get('word_count', 0)}
- Citations: {metrics.get('citation_count', 0)}
---

"""
        
        full_content = metrics_header + report_content
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        return report_path
    
    def _evaluate_thresholds(self, metrics: Dict[str, Any]) -> Dict[str, bool]:
        """Evaluate metrics against acceptance thresholds."""
        checks = {
            "duration_acceptable": metrics.get("duration_seconds", float('inf')) <= self.max_duration_seconds,
            "sufficient_sources": metrics.get("unique_sources", 0) >= self.min_sources,
            "coverage_acceptable": metrics.get("coverage_score", 0) >= self.min_coverage_score,
            "dead_links_acceptable": metrics.get("dead_link_rate", 1) <= self.max_dead_link_rate,
            "duplicates_acceptable": metrics.get("duplicate_rate", 1) <= self.max_duplicate_rate,
            "has_content": metrics.get("word_count", 0) >= 500
        }
        
        checks["overall_pass"] = all(checks.values())
        return checks
    
    async def run_evaluation_suite(self, topic_ids: Optional[List[str]] = None, 
                                  max_topics: Optional[int] = None) -> Dict[str, Any]:
        """
        Run evaluation on multiple topics.
        
        Args:
            topic_ids: Specific topic IDs to evaluate (optional)
            max_topics: Maximum number of topics to evaluate (optional)
        
        Returns:
            Aggregated evaluation results
        """
        topics = self.load_topics()
        
        if not topics:
            return {"error": "No topics loaded", "results": []}
        
        # Filter topics if specified
        if topic_ids:
            topics = [t for t in topics if t["id"] in topic_ids]
        
        if max_topics:
            topics = topics[:max_topics]
        
        logger.info(f"Running evaluation suite on {len(topics)} topics")
        
        # Run evaluations
        results = []
        for topic_data in topics:
            try:
                result = await self.run_single_evaluation(topic_data)
                results.append(result)
                
                # Brief pause between evaluations
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Failed to evaluate topic {topic_data['id']}: {e}")
                results.append({
                    "topic_id": topic_data["id"],
                    "success": False,
                    "error": str(e)
                })
        
        # Calculate summary statistics
        summary = self._calculate_summary(results)
        
        # Save summary report
        summary_path = self._save_summary(summary, results)
        
        return {
            "summary": summary,
            "results": results,
            "summary_path": str(summary_path)
        }
    
    def _calculate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics from evaluation results."""
        successful_results = [r for r in results if r.get("success", False)]
        
        if not successful_results:
            return {
                "total_topics": len(results),
                "successful_evaluations": 0,
                "success_rate": 0,
                "avg_duration": 0,
                "threshold_pass_rate": 0
            }
        
        # Calculate averages
        avg_duration = sum(r.get("duration", 0) for r in successful_results) / len(successful_results)
        avg_sources = sum(r.get("metrics", {}).get("unique_sources", 0) for r in successful_results) / len(successful_results)
        avg_coverage = sum(r.get("metrics", {}).get("coverage_score", 0) for r in successful_results) / len(successful_results)
        avg_word_count = sum(r.get("metrics", {}).get("word_count", 0) for r in successful_results) / len(successful_results)
        
        # Check threshold passes
        passed_count = 0
        for result in successful_results:
            metrics = result.get("metrics", {})
            checks = self._evaluate_thresholds(metrics)
            if checks["overall_pass"]:
                passed_count += 1
        
        return {
            "total_topics": len(results),
            "successful_evaluations": len(successful_results),
            "success_rate": len(successful_results) / len(results),
            "threshold_pass_rate": passed_count / len(successful_results) if successful_results else 0,
            "avg_duration": avg_duration,
            "avg_sources": avg_sources,
            "avg_coverage_score": avg_coverage,
            "avg_word_count": avg_word_count
        }
    
    def _save_summary(self, summary: Dict[str, Any], results: List[Dict[str, Any]]) -> Path:
        """Save evaluation summary to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_path = self.results_dir / f"evaluation_summary_{timestamp}.json"
        
        full_summary = {
            "timestamp": timestamp,
            "summary": summary,
            "detailed_results": results
        }
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(full_summary, f, indent=2, default=str)
        
        return summary_path


async def main():
    """Main evaluation entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Nova Brief evaluation harness")
    parser.add_argument("--topics", nargs="+", help="Specific topic IDs to evaluate")
    parser.add_argument("--max-topics", type=int, help="Maximum number of topics to evaluate")
    parser.add_argument("--quick", action="store_true", help="Run quick evaluation on 3 topics")
    
    args = parser.parse_args()
    
    harness = EvaluationHarness()
    
    if args.quick:
        # Quick evaluation on first 3 topics
        results = await harness.run_evaluation_suite(max_topics=3)
    else:
        # Full evaluation
        results = await harness.run_evaluation_suite(
            topic_ids=args.topics,
            max_topics=args.max_topics
        )
    
    # Print summary
    summary = results["summary"]
    print("\n" + "="*60)
    print("EVALUATION SUMMARY")
    print("="*60)
    print(f"Topics Evaluated: {summary['total_topics']}")
    print(f"Successful Runs: {summary['successful_evaluations']}")
    print(f"Success Rate: {summary['success_rate']:.1%}")
    print(f"Threshold Pass Rate: {summary['threshold_pass_rate']:.1%}")
    print(f"Average Duration: {summary['avg_duration']:.1f}s")
    print(f"Average Sources: {summary.get('avg_sources', 0):.1f}")
    print(f"Average Coverage: {summary.get('avg_coverage_score', 0):.1%}")
    print(f"Average Word Count: {summary.get('avg_word_count', 0):.0f}")
    print(f"\nSummary saved to: {results['summary_path']}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())