"""Multi-model evaluation harness for Nova Brief research agent."""

import asyncio
import json
import time
import sys
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import statistics

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.agent.orchestrator import run_research_pipeline
from src.storage.models import create_default_constraints, Constraints
from src.config import Config, validate_environment
from src.observability.logging import get_logger

logger = get_logger(__name__)


class MultiModelEvaluationHarness:
    """Multi-model evaluation harness for comparing research agent performance across different models."""
    
    # Default comparison sets
    DEFAULT_COMPARISON_SETS = {
        "default": [
            "gpt-oss-120b-openrouter-cerebras",  # GPT-OSS-120B with Cerebras
            "gpt-oss-120b-openrouter-default",   # GPT-OSS-120B with default routing  
            "claude-sonnet-4-openrouter-default" # Claude Sonnet 4 (larger model)
        ],
        "quick": [
            "gpt-oss-120b-openrouter-cerebras",
            "gpt-oss-120b-openrouter-default"
        ],
        "comprehensive": [
            "gpt-oss-120b-openrouter-cerebras",
            "gpt-oss-120b-openrouter-default",
            "claude-sonnet-4-openrouter-default",
            "gemini-2.5-flash-openrouter-default",
            "gpt-5-mini-openrouter-default"
        ]
    }
    
    def __init__(self, topics_file: str = "eval/topics.json"):
        self.topics_file = topics_file
        self.results: List[Dict[str, Any]] = []
        self.config = Config()
    
    async def run_multi_model_evaluation(
        self,
        models: Optional[List[str]] = None,
        quick: bool = False,
        max_topics: Optional[int] = None,
        comparison_set: str = "default"
    ) -> Dict[str, Any]:
        """
        Run evaluation across multiple models for comparison.
        
        Args:
            models: List of model keys to compare. If None, uses default comparison set.
            quick: If True, run with reduced constraints for faster evaluation
            max_topics: Maximum number of topics to evaluate
            comparison_set: Predefined comparison set to use if models not specified
        
        Returns:
            Multi-model evaluation results with comparative analysis
        """
        print("🧪 Starting Nova Brief Multi-Model Evaluation Harness")
        print("=" * 60)
        
        # Determine which models to evaluate
        if models is None:
            models = self.DEFAULT_COMPARISON_SETS.get(comparison_set, self.DEFAULT_COMPARISON_SETS["default"])
        
        # Validate model selections
        validation_result = self._validate_model_selections(models)
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": f"Model validation failed: {', '.join(validation_result['issues'])}"
            }
        
        # Load test topics
        topics = self._load_topics()
        if not topics:
            print("❌ No evaluation topics found")
            return {"success": False, "error": "No topics loaded"}
        
        # Limit topics if specified
        if max_topics:
            topics = topics[:max_topics]
        
        print(f"📋 Evaluating {len(topics)} topics across {len(models)} models")
        print(f"🤖 Models: {', '.join(models)}")
        if quick:
            print("⚡ Quick evaluation mode enabled")
        
        # Configure constraints for evaluation
        constraints = self._get_evaluation_constraints(quick)
        
        # Run evaluation across all models and topics
        start_time = time.time()
        
        # Results will be organized by model, then by topic
        model_results = {}
        
        for model_idx, model in enumerate(models, 1):
            print(f"\n{'='*40} Model {model_idx}/{len(models)}: {model} {'='*40}")
            
            model_config = self.config.get_available_models_dict().get(model)
            if model_config:
                print(f"🔧 Provider: {model_config.provider}")
                print(f"📦 Model ID: {model_config.model_id}")
                print(f"💡 Display Name: {model_config.display_name}")
            
            model_results[model] = []
            
            # Run each topic for this model
            for topic_idx, topic_data in enumerate(topics, 1):
                print(f"\n{'-'*20} Model: {model} | Topic {topic_idx}/{len(topics)} {'-'*20}")
                
                topic = topic_data["topic"]
                expected_elements = topic_data.get("expected_elements", [])
                
                print(f"🎯 Topic: {topic}")
                
                # Run research pipeline for this model-topic combination
                result = await self._evaluate_single_model_topic(
                    model,
                    topic,
                    constraints,
                    expected_elements
                )
                
                result["model"] = model
                result["topic"] = topic
                result["expected_elements"] = expected_elements
                model_results[model].append(result)
                
                # Print immediate results
                if result["success"]:
                    print(f"✅ Completed in {result['duration_s']:.1f}s")
                    print(f"📊 {result['word_count']} words, {result['sources_count']} sources")
                else:
                    print(f"❌ Failed: {result['error']}")
        
        # Calculate comparative metrics
        total_duration = time.time() - start_time
        evaluation_summary = self._calculate_comparative_metrics(model_results, total_duration)
        
        # Save results
        self._save_multi_model_results(evaluation_summary)
        
        # Print comparative summary
        self._print_comparative_summary(evaluation_summary)
        
        return evaluation_summary
    
    def _validate_model_selections(self, models: List[str]) -> Dict[str, Any]:
        """Validate that all selected models are available and configured."""
        issues = []
        warnings = []
        available_models = self.config.get_available_models_dict()
        
        if not models or len(models) == 0:
            issues.append("No models specified for comparison")
            return {"valid": False, "issues": issues, "warnings": warnings}
        
        if len(models) > 5:
            issues.append("Maximum of 5 models supported for comparison")
        
        for model in models:
            if model not in available_models:
                issues.append(f"Unknown model: {model}")
                continue
            
            # Validate model configuration
            validation = self.config.validate_model_config(model)
            if not validation["valid"]:
                issues.extend([f"{model}: {issue}" for issue in validation["issues"]])
            if validation["warnings"]:
                warnings.extend([f"{model}: {warning}" for warning in validation["warnings"]])
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }
    
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
    
    def _get_evaluation_constraints(self, quick: bool = False) -> Constraints:
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
    
    async def _evaluate_single_model_topic(
        self,
        model: str,
        topic: str,
        constraints: Constraints,
        expected_elements: List[str]
    ) -> Dict[str, Any]:
        """Evaluate research pipeline on a single model-topic combination."""
        
        topic_start_time = time.time()
        
        try:
            # Run research pipeline with specified model
            result = await run_research_pipeline(topic, constraints, selected_model=model)
            
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
                    "model_info": self.config.get_available_models_dict().get(model),
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
                    "coverage_score": 0.0,
                    "model_info": self.config.get_available_models_dict().get(model)
                }
        
        except Exception as e:
            duration = time.time() - topic_start_time
            logger.error(f"Evaluation failed for model '{model}' on topic '{topic}': {e}")
            
            return {
                "success": False,
                "duration_s": duration,
                "error": str(e),
                "word_count": 0,
                "sources_count": 0,
                "claims_count": 0,
                "citations_count": 0,
                "coverage_score": 0.0,
                "model_info": self.config.get_available_models_dict().get(model)
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
    
    def _calculate_comparative_metrics(
        self, 
        model_results: Dict[str, List[Dict[str, Any]]], 
        total_duration: float
    ) -> Dict[str, Any]:
        """Calculate comparative metrics across all models."""
        if not model_results:
            return {"success": False, "error": "No results to evaluate"}
        
        models = list(model_results.keys())
        comparative_metrics = {}
        
        # Calculate per-model metrics
        for model in models:
            results = model_results[model]
            successful_runs = [r for r in results if r["success"]]
            failed_runs = [r for r in results if not r["success"]]
            
            if successful_runs:
                avg_duration = statistics.mean(r["duration_s"] for r in successful_runs)
                avg_word_count = statistics.mean(r["word_count"] for r in successful_runs)
                avg_sources = statistics.mean(r["sources_count"] for r in successful_runs)
                avg_coverage = statistics.mean(r["coverage_score"] for r in successful_runs)
                
                # Calculate standard deviations for variability metrics
                duration_std = statistics.stdev(r["duration_s"] for r in successful_runs) if len(successful_runs) > 1 else 0
                word_count_std = statistics.stdev(r["word_count"] for r in successful_runs) if len(successful_runs) > 1 else 0
                coverage_std = statistics.stdev(r["coverage_score"] for r in successful_runs) if len(successful_runs) > 1 else 0
            else:
                avg_duration = avg_word_count = avg_sources = avg_coverage = 0
                duration_std = word_count_std = coverage_std = 0
            
            comparative_metrics[model] = {
                "total_topics": len(results),
                "successful_topics": len(successful_runs),
                "failed_topics": len(failed_runs),
                "success_rate": len(successful_runs) / len(results) * 100 if results else 0,
                "avg_duration_s": avg_duration,
                "avg_word_count": avg_word_count,
                "avg_sources_count": avg_sources,
                "avg_coverage_score": avg_coverage,
                "duration_std": duration_std,
                "word_count_std": word_count_std,
                "coverage_std": coverage_std,
                "model_info": successful_runs[0]["model_info"] if successful_runs else None
            }
        
        # Calculate cross-model comparative statistics
        all_successful = []
        for results in model_results.values():
            all_successful.extend([r for r in results if r["success"]])
        
        cross_model_stats = {}
        if all_successful:
            # Speed comparison (lower is better)
            speed_ranking = sorted(models, key=lambda m: comparative_metrics[m]["avg_duration_s"])
            
            # Quality comparison (higher coverage is better)
            quality_ranking = sorted(models, key=lambda m: comparative_metrics[m]["avg_coverage_score"], reverse=True)
            
            # Reliability comparison (higher success rate is better)
            reliability_ranking = sorted(models, key=lambda m: comparative_metrics[m]["success_rate"], reverse=True)
            
            # Word count comparison (for verbosity analysis)
            verbosity_ranking = sorted(models, key=lambda m: comparative_metrics[m]["avg_word_count"], reverse=True)
            
            cross_model_stats = {
                "speed_ranking": speed_ranking,
                "quality_ranking": quality_ranking,
                "reliability_ranking": reliability_ranking,
                "verbosity_ranking": verbosity_ranking
            }
        
        return {
            "success": True,
            "total_duration_s": total_duration,
            "models_evaluated": models,
            "model_metrics": comparative_metrics,
            "cross_model_stats": cross_model_stats,
            "detailed_results": model_results
        }
    
    def _save_multi_model_results(self, evaluation_summary: Dict[str, Any]):
        """Save multi-model evaluation results to file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = f"eval/multi_model_results_{timestamp}.json"
            
            os.makedirs(os.path.dirname(results_file), exist_ok=True)
            
            with open(results_file, 'w') as f:
                json.dump(evaluation_summary, f, indent=2, default=str)
            
            print(f"💾 Multi-model results saved to: {results_file}")
        
        except Exception as e:
            print(f"⚠️  Could not save results: {e}")
    
    def _print_comparative_summary(self, summary: Dict[str, Any]):
        """Print multi-model comparative summary."""
        print(f"\n{'='*60}")
        print("📊 MULTI-MODEL EVALUATION SUMMARY")
        print("=" * 60)
        
        if not summary["success"]:
            print(f"❌ Evaluation failed: {summary.get('error')}")
            return
        
        models = summary["models_evaluated"]
        print(f"Models Evaluated: {len(models)}")
        print(f"Total Duration: {summary['total_duration_s']:.1f}s")
        
        # Print per-model summary
        print(f"\n📋 Per-Model Performance:")
        model_metrics = summary["model_metrics"]
        
        for model in models:
            metrics = model_metrics[model]
            print(f"\n🤖 {model}")
            if metrics["model_info"]:
                print(f"     Provider: {metrics['model_info'].provider}")
                print(f"     Display: {metrics['model_info'].display_name}")
            print(f"     Success Rate: {metrics['success_rate']:.1f}% ({metrics['successful_topics']}/{metrics['total_topics']})")
            if metrics['successful_topics'] > 0:
                print(f"     Avg Duration: {metrics['avg_duration_s']:.1f}s (±{metrics['duration_std']:.1f}s)")
                print(f"     Avg Word Count: {metrics['avg_word_count']:.0f} (±{metrics['word_count_std']:.0f})")
                print(f"     Avg Sources: {metrics['avg_sources_count']:.1f}")
                print(f"     Avg Coverage: {metrics['avg_coverage_score']:.1%} (±{metrics['coverage_std']:.1%})")
        
        # Print comparative rankings
        if "cross_model_stats" in summary and summary["cross_model_stats"]:
            stats = summary["cross_model_stats"]
            print(f"\n🏆 Comparative Rankings:")
            
            print(f"🚀 Speed (Fastest to Slowest):")
            for i, model in enumerate(stats["speed_ranking"], 1):
                duration = model_metrics[model]["avg_duration_s"]
                print(f"     {i}. {model}: {duration:.1f}s")
            
            print(f"🎯 Quality (Best to Worst Coverage):")
            for i, model in enumerate(stats["quality_ranking"], 1):
                coverage = model_metrics[model]["avg_coverage_score"]
                print(f"     {i}. {model}: {coverage:.1%}")
            
            print(f"🛡️  Reliability (Most to Least Successful):")
            for i, model in enumerate(stats["reliability_ranking"], 1):
                success_rate = model_metrics[model]["success_rate"]
                print(f"     {i}. {model}: {success_rate:.1f}%")
            
            print(f"📝 Verbosity (Most to Least Words):")
            for i, model in enumerate(stats["verbosity_ranking"], 1):
                word_count = model_metrics[model]["avg_word_count"]
                print(f"     {i}. {model}: {word_count:.0f} words")


async def main():
    """Main multi-model evaluation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Nova Brief Multi-Model Evaluation Harness")
    parser.add_argument("--models", nargs="+", help="List of model keys to compare (1-5 models)")
    parser.add_argument("--comparison-set", choices=["default", "quick", "comprehensive"], 
                       default="default", help="Predefined comparison set")
    parser.add_argument("--quick", action="store_true", help="Run quick evaluation")
    parser.add_argument("--max-topics", type=int, help="Maximum number of topics to evaluate")
    parser.add_argument("--topics-file", default="eval/topics.json", help="Topics file path")
    parser.add_argument("--list-models", action="store_true", help="List available models and exit")
    
    args = parser.parse_args()
    
    # List available models if requested
    if args.list_models:
        config = Config()
        available_models = config.get_available_models_dict()
        print("📋 Available Models:")
        for key, model_config in available_models.items():
            cerebras_indicator = " 🧠" if model_config.supports_cerebras else ""
            print(f"  {key}: {model_config.display_name}{cerebras_indicator}")
        
        print(f"\n🎯 Default Comparison Sets:")
        for set_name, models in MultiModelEvaluationHarness.DEFAULT_COMPARISON_SETS.items():
            print(f"  {set_name}: {', '.join(models)}")
        return True
    
    # Validate environment
    if not validate_environment():
        print("❌ Environment validation failed. Please check configuration.")
        return False
    
    # Run multi-model evaluation
    harness = MultiModelEvaluationHarness(args.topics_file)
    
    try:
        summary = await harness.run_multi_model_evaluation(
            models=args.models,
            quick=args.quick,
            max_topics=args.max_topics,
            comparison_set=args.comparison_set
        )
        
        # Determine exit code based on overall success
        if summary["success"]:
            model_metrics = summary["model_metrics"]
            overall_success_rate = statistics.mean([
                metrics["success_rate"] for metrics in model_metrics.values()
            ])
            
            if overall_success_rate >= 80:
                print("🎉 Multi-Model Evaluation PASSED - High success rate across models")
                return True
            elif overall_success_rate >= 60:
                print("⚠️  Multi-Model Evaluation PARTIAL - Moderate success rate across models")
                return True
            else:
                print("❌ Multi-Model Evaluation FAILED - Low success rate across models")
                return False
        else:
            print("❌ Multi-Model Evaluation FAILED - Could not complete")
            return False
    
    except Exception as e:
        print(f"❌ Multi-model evaluation failed with exception: {e}")
        logger.error(f"Multi-model evaluation harness failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)