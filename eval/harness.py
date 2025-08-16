"""Evaluation harness for Nova Brief research agent."""

import asyncio
import json
import time
import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.agent.orchestrator import run_research_pipeline
from src.storage.models import create_default_constraints, Constraints
from src.config import validate_environment
from src.observability.logging import get_logger

logger = get_logger(__name__)


class EvaluationHarness:
    """Evaluation harness for testing research agent performance."""
    
    def __init__(self, topics_file: str = "eval/topics.json"):
        self.topics_file = topics_file
        self.results: List[Dict[str, Any]] = []
    
    async def run_evaluation(
        self, 
        quick: bool = False,
        max_topics: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Run evaluation on test topics.
        
        Args:
            quick: If True, run with reduced constraints for faster evaluation
            max_topics: Maximum number of topics to evaluate
        
        Returns:
            Evaluation results summary
        """
        print("🧪 Starting Nova Brief Evaluation Harness")
        print("=" * 50)
        
        # Load test topics
        topics = self._load_topics()
        if not topics:
            print("❌ No evaluation topics found")
            return {"success": False, "error": "No topics loaded"}
        
        # Limit topics if specified
        if max_topics:
            topics = topics[:max_topics]
        
        print(f"📋 Evaluating {len(topics)} topics")
        if quick:
            print("⚡ Quick evaluation mode enabled")
        
        # Configure constraints for evaluation
        constraints = self._get_evaluation_constraints(quick)
        
        # Run evaluation on each topic
        start_time = time.time()
        
        for i, topic_data in enumerate(topics, 1):
            print(f"\n{'='*20} Topic {i}/{len(topics)} {'='*20}")
            
            topic = topic_data["topic"]
            expected_elements = topic_data.get("expected_elements", [])
            
            print(f"🎯 Topic: {topic}")
            print(f"📝 Expected elements: {', '.join(expected_elements)}")
            
            # Run research pipeline
            result = await self._evaluate_single_topic(
                topic, 
                constraints, 
                expected_elements
            )
            
            self.results.append({
                "topic": topic,
                "expected_elements": expected_elements,
                **result
            })
            
            # Print immediate results
            if result["success"]:
                print(f"✅ Completed in {result['duration_s']:.1f}s")
                print(f"📊 {result['word_count']} words, {result['sources_count']} sources")
            else:
                print(f"❌ Failed: {result['error']}")
        
        # Calculate overall metrics
        total_duration = time.time() - start_time
        evaluation_summary = self._calculate_evaluation_metrics(total_duration)
        
        # Save results
        self._save_results(evaluation_summary)
        
        # Print summary
        self._print_evaluation_summary(evaluation_summary)
        
        return evaluation_summary
    
    def _load_topics(self) -> List[Dict[str, Any]]:
        """Load evaluation topics from JSON file."""
        try:
            if not os.path.exists(self.topics_file):
                # Create default topics if file doesn't exist
                default_topics = self._create_default_topics()
                self._save_topics(default_topics)
                return default_topics
            
            with open(self.topics_file, 'r') as f:
                topics_data = json.load(f)
            
            return topics_data.get("topics", [])
        
        except Exception as e:
            print(f"❌ Error loading topics: {e}")
            return []
    
    def _create_default_topics(self) -> List[Dict[str, Any]]:
        """Create default evaluation topics."""
        return [
            {
                "topic": "Impact of artificial intelligence on healthcare in 2024",
                "expected_elements": [
                    "AI applications in healthcare",
                    "Current implementations",
                    "Benefits and challenges",
                    "Future prospects"
                ]
            },
            {
                "topic": "Climate change mitigation strategies and their effectiveness",
                "expected_elements": [
                    "Renewable energy adoption",
                    "Carbon capture technologies",
                    "Policy measures",
                    "International cooperation"
                ]
            },
            {
                "topic": "Remote work trends and productivity impacts post-2020",
                "expected_elements": [
                    "Adoption rates",
                    "Productivity studies",
                    "Employee satisfaction",
                    "Company policies"
                ]
            },
            {
                "topic": "Cryptocurrency regulation developments in major economies",
                "expected_elements": [
                    "Regulatory frameworks",
                    "Government positions", 
                    "Market impacts",
                    "Compliance requirements"
                ]
            },
            {
                "topic": "Electric vehicle market growth and infrastructure challenges",
                "expected_elements": [
                    "Market statistics",
                    "Charging infrastructure",
                    "Government incentives",
                    "Consumer adoption"
                ]
            }
        ]
    
    def _save_topics(self, topics: List[Dict[str, Any]]):
        """Save topics to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.topics_file), exist_ok=True)
            
            topics_data = {
                "description": "Evaluation topics for Nova Brief research agent",
                "version": "1.0",
                "topics": topics
            }
            
            with open(self.topics_file, 'w') as f:
                json.dump(topics_data, f, indent=2)
            
            print(f"💾 Created default topics file: {self.topics_file}")
        
        except Exception as e:
            print(f"❌ Error saving topics: {e}")
    
    def _get_evaluation_constraints(self, quick: bool = False):
        """Get constraints configured for evaluation."""
        constraints = create_default_constraints()
        
        if quick:
            # Reduce constraints for faster evaluation
            constraints["max_rounds"] = 1
            constraints["per_domain_cap"] = 2
            constraints["fetch_timeout_s"] = 10.0
        else:
            # Standard evaluation constraints
            constraints["max_rounds"] = 2
            constraints["per_domain_cap"] = 3
            constraints["fetch_timeout_s"] = 15.0
        
        return constraints
    
    async def _evaluate_single_topic(
        self,
        topic: str,
        constraints: Constraints,
        expected_elements: List[str]
    ) -> Dict[str, Any]:
        """Evaluate research pipeline on a single topic."""
        
        topic_start_time = time.time()
        
        try:
            # Run research pipeline
            result = await run_research_pipeline(topic, constraints)
            
            duration = time.time() - topic_start_time
            
            if result["success"]:
                # Extract metrics from result
                state = result["state"]
                report = result["report"]
                metrics = result["metrics"]
                
                # Evaluate content coverage
                coverage_score = self._evaluate_content_coverage(
                    report["report_md"], 
                    expected_elements
                )
                
                return {
                    "success": True,
                    "duration_s": duration,
                    "word_count": report["word_count"],
                    "sources_count": metrics["sources_count"],
                    "claims_count": len(state["claims"]),
                    "citations_count": len(state["citations"]),
                    "coverage_score": coverage_score,
                    "report_md": report["report_md"],
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "duration_s": duration,
                    "error": result["error"],
                    "word_count": 0,
                    "sources_count": 0,
                    "claims_count": 0,
                    "citations_count": 0,
                    "coverage_score": 0.0
                }
        
        except Exception as e:
            duration = time.time() - topic_start_time
            logger.error(f"Evaluation failed for topic '{topic}': {e}")
            
            return {
                "success": False,
                "duration_s": duration,
                "error": str(e),
                "word_count": 0,
                "sources_count": 0,
                "claims_count": 0,
                "citations_count": 0,
                "coverage_score": 0.0
            }
    
    def _evaluate_content_coverage(
        self, 
        report_content: str, 
        expected_elements: List[str]
    ) -> float:
        """Evaluate how well the report covers expected elements."""
        if not expected_elements:
            return 1.0
        
        content_lower = report_content.lower()
        covered_elements = 0
        
        for element in expected_elements:
            # Simple keyword matching - could be enhanced with semantic similarity
            element_keywords = element.lower().split()
            
            # Check if any significant words from the element appear in content
            matches = sum(1 for keyword in element_keywords if len(keyword) > 3 and keyword in content_lower)
            
            if matches >= len(element_keywords) * 0.5:  # At least 50% of keywords found
                covered_elements += 1
        
        return covered_elements / len(expected_elements)
    
    def _calculate_evaluation_metrics(self, total_duration: float) -> Dict[str, Any]:
        """Calculate overall evaluation metrics."""
        if not self.results:
            return {"success": False, "error": "No results to evaluate"}
        
        successful_runs = [r for r in self.results if r["success"]]
        failed_runs = [r for r in self.results if not r["success"]]
        
        if successful_runs:
            avg_duration = sum(r["duration_s"] for r in successful_runs) / len(successful_runs)
            avg_word_count = sum(r["word_count"] for r in successful_runs) / len(successful_runs)
            avg_sources = sum(r["sources_count"] for r in successful_runs) / len(successful_runs)
            avg_coverage = sum(r["coverage_score"] for r in successful_runs) / len(successful_runs)
        else:
            avg_duration = avg_word_count = avg_sources = avg_coverage = 0
        
        return {
            "success": True,
            "total_topics": len(self.results),
            "successful_topics": len(successful_runs),
            "failed_topics": len(failed_runs),
            "success_rate": len(successful_runs) / len(self.results) * 100,
            "total_duration_s": total_duration,
            "avg_duration_s": avg_duration,
            "avg_word_count": avg_word_count,
            "avg_sources_count": avg_sources,
            "avg_coverage_score": avg_coverage,
            "results": self.results
        }
    
    def _save_results(self, evaluation_summary: Dict[str, Any]):
        """Save evaluation results to file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = f"eval/results_{timestamp}.json"
            
            os.makedirs(os.path.dirname(results_file), exist_ok=True)
            
            with open(results_file, 'w') as f:
                json.dump(evaluation_summary, f, indent=2, default=str)
            
            print(f"💾 Results saved to: {results_file}")
        
        except Exception as e:
            print(f"⚠️  Could not save results: {e}")
    
    def _print_evaluation_summary(self, summary: Dict[str, Any]):
        """Print evaluation summary."""
        print(f"\n{'='*50}")
        print("📊 EVALUATION SUMMARY")
        print("=" * 50)
        
        if not summary["success"]:
            print(f"❌ Evaluation failed: {summary.get('error')}")
            return
        
        print(f"Topics Evaluated: {summary['total_topics']}")
        print(f"Success Rate: {summary['success_rate']:.1f}% ({summary['successful_topics']}/{summary['total_topics']})")
        print(f"Total Duration: {summary['total_duration_s']:.1f}s")
        
        if summary['successful_topics'] > 0:
            print(f"Average Duration: {summary['avg_duration_s']:.1f}s per topic")
            print(f"Average Word Count: {summary['avg_word_count']:.0f} words")
            print(f"Average Sources: {summary['avg_sources_count']:.1f} sources")
            print(f"Average Coverage: {summary['avg_coverage_score']:.1%}")
        
        # Print individual results
        print(f"\n📋 Individual Results:")
        for i, result in enumerate(summary['results'], 1):
            status = "✅" if result["success"] else "❌"
            topic = result["topic"][:60] + "..." if len(result["topic"]) > 60 else result["topic"]
            
            if result["success"]:
                print(f"{status} {i:2d}. {topic}")
                print(f"     Duration: {result['duration_s']:.1f}s, Words: {result['word_count']}, "
                      f"Sources: {result['sources_count']}, Coverage: {result['coverage_score']:.1%}")
            else:
                print(f"{status} {i:2d}. {topic}")
                print(f"     Error: {result['error']}")


async def main():
    """Main evaluation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Nova Brief Evaluation Harness")
    parser.add_argument("--quick", action="store_true", help="Run quick evaluation")
    parser.add_argument("--max-topics", type=int, help="Maximum number of topics to evaluate")
    parser.add_argument("--topics-file", default="eval/topics.json", help="Topics file path")
    
    args = parser.parse_args()
    
    # Validate environment
    if not validate_environment():
        print("❌ Environment validation failed. Please check configuration.")
        return False
    
    # Run evaluation
    harness = EvaluationHarness(args.topics_file)
    
    try:
        summary = await harness.run_evaluation(
            quick=args.quick,
            max_topics=args.max_topics
        )
        
        # Determine exit code based on success rate
        if summary["success"]:
            success_rate = summary["success_rate"]
            if success_rate >= 80:
                print("🎉 Evaluation PASSED - High success rate")
                return True
            elif success_rate >= 60:
                print("⚠️  Evaluation PARTIAL - Moderate success rate")
                return True
            else:
                print("❌ Evaluation FAILED - Low success rate")
                return False
        else:
            print("❌ Evaluation FAILED - Could not complete")
            return False
    
    except Exception as e:
        print(f"❌ Evaluation failed with exception: {e}")
        logger.error(f"Evaluation harness failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)