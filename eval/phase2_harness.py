#!/usr/bin/env python3
"""Enhanced evaluation harness for Phase 2 Agent Intelligence capabilities."""

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
from src.agent.critic import critique_report, generate_improvement_suggestions
from src.agent.analyst import analyze
from src.agent.writer import write
from src.storage.models import create_default_constraints
from src.config import Config, validate_environment
from src.observability.logging import get_logger

logger = get_logger(__name__)


class Phase2EvaluationHarness:
    """Enhanced evaluation harness for Phase 2 Agent Intelligence capabilities."""
    
    def __init__(self, topics_file: str = "eval/topics.json"):
        self.topics_file = topics_file
        self.results: List[Dict[str, Any]] = []
    
    async def run_phase2_evaluation(
        self,
        quick: bool = False,
        max_topics: Optional[int] = None,
        test_modes: Optional[List[str]] = None,
        test_audiences: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Run comprehensive Phase 2 Agent Intelligence evaluation.
        
        Args:
            quick: If True, run with reduced scope for faster evaluation
            max_topics: Maximum number of topics to evaluate
            test_modes: Research modes to test (default: all)
            test_audiences: Target audiences to test (default: all)
        
        Returns:
            Evaluation results summary
        """
        print("🚀 Starting Phase 2 Agent Intelligence Evaluation")
        print("=" * 60)
        
        # Load test topics
        topics = self._load_topics()
        if not topics:
            print("❌ No evaluation topics found")
            return {"success": False, "error": "No topics loaded"}
        
        # Limit topics if specified
        if max_topics:
            topics = topics[:max_topics]
        
        # Set defaults for test parameters
        if test_modes is None:
            test_modes = ["🚀 Quick Brief", "⚖️ Balanced Analysis", "🔬 Deep Dive"]
            if quick:
                test_modes = ["🚀 Quick Brief", "⚖️ Balanced Analysis"]  # Skip Deep Dive in quick mode
        
        if test_audiences is None:
            test_audiences = ["Executive", "Technical", "General"]
            if quick:
                test_audiences = ["General", "Executive"]  # Skip Technical in quick mode
        
        print(f"📋 Evaluating {len(topics)} topics")
        print(f"🎯 Research modes: {', '.join(test_modes)}")
        print(f"👥 Target audiences: {', '.join(test_audiences)}")
        if quick:
            print("⚡ Quick evaluation mode enabled")
        
        # Run comprehensive evaluation
        start_time = time.time()
        
        for i, topic_data in enumerate(topics, 1):
            print(f"\n{'='*25} Topic {i}/{len(topics)} {'='*25}")
            
            topic = topic_data["topic"]
            expected_elements = topic_data.get("expected_elements", [])
            
            print(f"🎯 Topic: {topic}")
            print(f"📝 Expected elements: {', '.join(expected_elements)}")
            
            # Test each research mode with each audience
            for mode in test_modes:
                for audience in test_audiences:
                    print(f"\n  🔬 Testing: {mode} → {audience} audience")
                    
                    result = await self._evaluate_phase2_combination(
                        topic,
                        mode,
                        audience,
                        expected_elements,
                        quick
                    )
                    
                    self.results.append({
                        "topic": topic,
                        "research_mode": mode,
                        "target_audience": audience,
                        "expected_elements": expected_elements,
                        **result
                    })
                    
                    # Print immediate results
                    if result["success"]:
                        print(f"    ✅ Completed in {result['duration_s']:.1f}s")
                        print(f"    📊 {result['word_count']} words, {result['sources_count']} sources")
                        if result.get("contradictions_found", 0) > 0:
                            print(f"    ⚠️  {result['contradictions_found']} contradictions detected")
                        if result.get("critic_score"):
                            print(f"    📝 Critic score: {result['critic_score']:.1f}/10")
                    else:
                        print(f"    ❌ Failed: {result['error']}")
        
        # Calculate comprehensive metrics
        total_duration = time.time() - start_time
        evaluation_summary = self._calculate_phase2_metrics(total_duration)
        
        # Save results
        self._save_results(evaluation_summary)
        
        # Print summary
        self._print_phase2_summary(evaluation_summary)
        
        return evaluation_summary
    
    async def _evaluate_phase2_combination(
        self,
        topic: str,
        research_mode: str,
        target_audience: str,
        expected_elements: List[str],
        quick: bool = False
    ) -> Dict[str, Any]:
        """Evaluate a specific combination of research mode and target audience."""
        
        start_time = time.time()
        
        try:
            # Configure constraints based on research mode
            constraints = self._get_mode_constraints(research_mode, quick)
            
            # Update selected research mode in config
            original_mode = Config.SELECTED_RESEARCH_MODE
            Config.SELECTED_RESEARCH_MODE = research_mode
            
            try:
                # Run research pipeline
                from src.storage.models import Constraints
                constraints_obj = Constraints(**constraints) if isinstance(constraints, dict) else constraints
                result = await run_research_pipeline(topic, constraints_obj)
                
                if not result["success"]:
                    return {
                        "success": False,
                        "duration_s": time.time() - start_time,
                        "error": result["error"],
                        **self._empty_metrics()
                    }
                
                # Extract pipeline results
                state = result["state"]
                report = result["report"]
                metrics = result["metrics"]
                
                # Test Critic Agent (if report available)
                critic_metrics = await self._test_critic_agent(
                    report["report_md"], 
                    topic, 
                    target_audience,
                    state.get("sources", [])
                )
                
                # Test Contradiction Detection
                contradiction_metrics = self._test_contradiction_detection(state)
                
                # Test Structural Content Analysis
                structural_metrics = self._test_structural_content(state)
                
                # Test Multi-Provider Search
                search_metrics = self._test_multi_provider_search(state)
                
                # Test Audience Adaptation
                audience_metrics = self._test_audience_adaptation(
                    report["report_md"], 
                    target_audience
                )
                
                # Test Research Mode Effectiveness
                mode_metrics = self._test_research_mode_effectiveness(
                    result, 
                    research_mode,
                    constraints
                )
                
                # Calculate coverage metrics
                coverage_score = self._evaluate_content_coverage(
                    report["report_md"], 
                    expected_elements
                )
                
                duration = time.time() - start_time
                
                return {
                    "success": True,
                    "duration_s": duration,
                    "word_count": report["word_count"],
                    "sources_count": metrics["sources_count"],
                    "claims_count": len(state.get("claims", [])),
                    "citations_count": len(state.get("citations", [])),
                    "coverage_score": coverage_score,
                    "error": None,
                    # Phase 2 specific metrics
                    **critic_metrics,
                    **contradiction_metrics,
                    **structural_metrics,
                    **search_metrics,
                    **audience_metrics,
                    **mode_metrics
                }
                
            finally:
                # Restore original research mode
                Config.SELECTED_RESEARCH_MODE = original_mode
        
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Phase 2 evaluation failed for topic '{topic}': {e}")
            
            return {
                "success": False,
                "duration_s": duration,
                "error": str(e),
                **self._empty_metrics()
            }
    
    async def _test_critic_agent(
        self,
        report_content: str,
        topic: str,
        target_audience: str,
        sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Test Critic agent quality assurance capabilities."""
        
        try:
            # Run critique
            critique_result = await critique_report(
                report_content=report_content,
                research_topic=topic,
                target_audience=target_audience,
                sources_used=sources
            )
            
            if critique_result["success"]:
                critique = critique_result["critique"]
                overall_score = critique.get("overall_score", 0)
                should_revise = critique_result.get("should_revise", False)
                
                # Generate improvement suggestions
                suggestions_result = await generate_improvement_suggestions(
                    critique_data=critique,
                    report_content=report_content,
                    target_audience=target_audience
                )
                
                suggestions_count = 0
                if suggestions_result["success"]:
                    suggestions = suggestions_result["suggestions"]
                    suggestions_count = (
                        len(suggestions.get("immediate_fixes", [])) +
                        len(suggestions.get("content_enhancements", [])) +
                        len(suggestions.get("structural_improvements", [])) +
                        len(suggestions.get("source_improvements", []))
                    )
                
                return {
                    "critic_success": True,
                    "critic_score": overall_score,
                    "critic_should_revise": should_revise,
                    "critic_suggestions_count": suggestions_count,
                    "critic_error": None
                }
            else:
                return {
                    "critic_success": False,
                    "critic_score": 0,
                    "critic_should_revise": False,
                    "critic_suggestions_count": 0,
                    "critic_error": critique_result.get("error", "Unknown error")
                }
        
        except Exception as e:
            return {
                "critic_success": False,
                "critic_score": 0,
                "critic_should_revise": False,
                "critic_suggestions_count": 0,
                "critic_error": str(e)
            }
    
    def _test_contradiction_detection(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Test Analyst agent contradiction detection capabilities."""
        
        claims = state.get("claims", [])
        contradictions_found = 0
        supporting_clusters_found = 0
        
        for claim in claims:
            # Check if claim has contradiction data
            if claim.get("contradictions"):
                contradictions_found += len(claim["contradictions"])
            
            # Check if claim has supporting clusters
            if claim.get("supporting_clusters"):
                supporting_clusters_found += len(claim["supporting_clusters"])
        
        return {
            "contradictions_found": contradictions_found,
            "supporting_clusters_found": supporting_clusters_found,
            "contradiction_detection_active": contradictions_found > 0 or supporting_clusters_found > 0
        }
    
    def _test_structural_content(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Test Reader agent structural content extraction capabilities."""
        
        documents = state.get("documents", [])
        structural_features_found = 0
        content_types_detected = set()
        
        for doc in documents:
            source_meta = doc.get("source_meta", {})
            
            # Check for enhanced structural metadata
            structure = source_meta.get("structure", {})
            classification = source_meta.get("classification", {})
            enhanced_metadata = source_meta.get("enhanced_metadata", {})
            
            if structure:
                # Count structural features
                features = ["headings", "sections", "lists", "tables", "citations"]
                for feature in features:
                    if structure.get(feature):
                        structural_features_found += 1
            
            if classification:
                primary_type = classification.get("primary_type")
                if primary_type and primary_type != "unknown":
                    content_types_detected.add(primary_type)
        
        return {
            "structural_features_found": structural_features_found,
            "content_types_detected": len(content_types_detected),
            "content_types_list": list(content_types_detected),
            "structural_extraction_active": structural_features_found > 0
        }
    
    def _test_multi_provider_search(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Test multi-provider search effectiveness."""
        
        # Check for search diversity in sources
        sources = state.get("sources", [])
        domains = set()
        
        for source in sources:
            url = source.get("url", "")
            if url:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc
                    domains.add(domain)
                except:
                    pass
        
        return {
            "source_domains_count": len(domains),
            "source_diversity_score": len(domains) / max(1, len(sources)),
            "multi_provider_effective": len(domains) > 1
        }
    
    def _test_audience_adaptation(self, report_content: str, target_audience: str) -> Dict[str, Any]:
        """Test Writer agent audience adaptation capabilities."""
        
        # Simple metrics for audience adaptation
        word_count = len(report_content.split())
        sentence_count = report_content.count('.') + report_content.count('!') + report_content.count('?')
        avg_sentence_length = word_count / max(1, sentence_count)
        
        # Check for audience-specific language patterns
        technical_terms = len([word for word in report_content.lower().split() 
                              if word in ["api", "algorithm", "implementation", "architecture", "framework"]])
        
        executive_terms = len([word for word in report_content.lower().split()
                              if word in ["strategy", "impact", "roi", "business", "market", "growth"]])
        
        # Determine if content matches expected audience style
        audience_match_score = 0.5  # Default neutral score
        
        if target_audience == "Technical" and technical_terms > executive_terms:
            audience_match_score = 0.8
        elif target_audience == "Executive" and executive_terms > technical_terms:
            audience_match_score = 0.8
        elif target_audience == "General" and avg_sentence_length < 20:
            audience_match_score = 0.7
        
        return {
            "audience_adaptation_score": audience_match_score,
            "avg_sentence_length": avg_sentence_length,
            "technical_terms_count": technical_terms,
            "executive_terms_count": executive_terms,
            "audience_match_detected": audience_match_score > 0.6
        }
    
    def _test_research_mode_effectiveness(
        self,
        result: Dict[str, Any],
        research_mode: str,
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Test research mode effectiveness and constraint adherence."""
        
        metrics = result.get("metrics", {})
        duration = metrics.get("duration_s", 0)
        
        # Check if constraints were followed
        expected_rounds = constraints.get("max_rounds", 1)
        expected_timeout = constraints.get("fetch_timeout_s", 15)
        
        # Mode-specific expectations
        mode_expectations = {
            "🚀 Quick Brief": {"max_duration": 120, "min_sources": 3, "target_words": 500},
            "⚖️ Balanced Analysis": {"max_duration": 300, "min_sources": 5, "target_words": 1000},
            "🔬 Deep Dive": {"max_duration": 600, "min_sources": 8, "target_words": 1500}
        }
        
        expectations = mode_expectations.get(research_mode, {})
        
        # Calculate effectiveness score
        effectiveness_score = 1.0
        
        # Check duration
        max_duration = expectations.get("max_duration", 600)
        if duration > max_duration:
            effectiveness_score -= 0.2
        
        # Check source count
        min_sources = expectations.get("min_sources", 3)
        sources_count = metrics.get("sources_count", 0)
        if sources_count < min_sources:
            effectiveness_score -= 0.3
        
        # Check word count
        target_words = expectations.get("target_words", 1000)
        word_count = result.get("report", {}).get("word_count", 0)
        word_ratio = word_count / max(1, target_words)
        if word_ratio < 0.7 or word_ratio > 1.5:  # 70%-150% of target
            effectiveness_score -= 0.2
        
        effectiveness_score = max(0.0, effectiveness_score)
        
        return {
            "mode_effectiveness_score": effectiveness_score,
            "mode_constraints_followed": duration <= max_duration,
            "mode_target_met": sources_count >= min_sources and 0.7 <= word_ratio <= 1.5
        }
    
    def _get_mode_constraints(self, research_mode: str, quick: bool = False) -> Dict[str, Any]:
        """Get constraints for specific research mode."""
        
        # Apply research mode settings
        mode_constraints = Config.apply_research_mode(research_mode)
        
        # Override for quick evaluation
        if quick:
            mode_constraints["max_rounds"] = min(mode_constraints.get("max_rounds", 1), 1)
            mode_constraints["per_domain_cap"] = min(mode_constraints.get("per_domain_cap", 2), 2)
            mode_constraints["fetch_timeout_s"] = min(mode_constraints.get("fetch_timeout_s", 10), 10)
        
        return mode_constraints
    
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
            element_keywords = element.lower().split()
            matches = sum(1 for keyword in element_keywords 
                         if len(keyword) > 3 and keyword in content_lower)
            
            if matches >= len(element_keywords) * 0.5:
                covered_elements += 1
        
        return covered_elements / len(expected_elements)
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics for failed evaluations."""
        return {
            "word_count": 0,
            "sources_count": 0,
            "claims_count": 0,
            "citations_count": 0,
            "coverage_score": 0.0,
            "critic_success": False,
            "critic_score": 0,
            "critic_should_revise": False,
            "critic_suggestions_count": 0,
            "critic_error": "Pipeline failed",
            "contradictions_found": 0,
            "supporting_clusters_found": 0,
            "contradiction_detection_active": False,
            "structural_features_found": 0,
            "content_types_detected": 0,
            "content_types_list": [],
            "structural_extraction_active": False,
            "source_domains_count": 0,
            "source_diversity_score": 0.0,
            "multi_provider_effective": False,
            "audience_adaptation_score": 0.0,
            "avg_sentence_length": 0,
            "technical_terms_count": 0,
            "executive_terms_count": 0,
            "audience_match_detected": False,
            "mode_effectiveness_score": 0.0,
            "mode_constraints_followed": False,
            "mode_target_met": False
        }
    
    def _load_topics(self) -> List[Dict[str, Any]]:
        """Load evaluation topics from JSON file."""
        try:
            if not os.path.exists(self.topics_file):
                # Create enhanced topics for Phase 2 testing
                default_topics = self._create_phase2_topics()
                self._save_topics(default_topics)
                return default_topics
            
            with open(self.topics_file, 'r') as f:
                topics_data = json.load(f)
            
            return topics_data.get("topics", [])
        
        except Exception as e:
            print(f"❌ Error loading topics: {e}")
            return []
    
    def _create_phase2_topics(self) -> List[Dict[str, Any]]:
        """Create enhanced evaluation topics for Phase 2 testing."""
        return [
            {
                "topic": "Artificial intelligence impact on healthcare diagnostics in 2024",
                "expected_elements": [
                    "AI diagnostic tools",
                    "Accuracy improvements", 
                    "Implementation challenges",
                    "Regulatory considerations",
                    "Healthcare provider adoption"
                ]
            },
            {
                "topic": "Climate change mitigation through renewable energy technologies",
                "expected_elements": [
                    "Solar and wind energy",
                    "Energy storage solutions",
                    "Grid integration challenges",
                    "Cost-benefit analysis",
                    "Policy support mechanisms"
                ]
            },
            {
                "topic": "Remote work productivity and employee wellbeing post-pandemic",
                "expected_elements": [
                    "Productivity metrics",
                    "Mental health impacts",
                    "Work-life balance",
                    "Company policies",
                    "Technology infrastructure"
                ]
            }
        ]
    
    def _save_topics(self, topics: List[Dict[str, Any]]):
        """Save topics to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.topics_file), exist_ok=True)
            
            topics_data = {
                "description": "Phase 2 Agent Intelligence evaluation topics",
                "version": "2.0",
                "topics": topics
            }
            
            with open(self.topics_file, 'w') as f:
                json.dump(topics_data, f, indent=2)
            
            print(f"💾 Created Phase 2 topics file: {self.topics_file}")
        
        except Exception as e:
            print(f"❌ Error saving topics: {e}")
    
    def _calculate_phase2_metrics(self, total_duration: float) -> Dict[str, Any]:
        """Calculate comprehensive Phase 2 evaluation metrics."""
        if not self.results:
            return {"success": False, "error": "No results to evaluate"}
        
        successful_runs = [r for r in self.results if r["success"]]
        failed_runs = [r for r in self.results if not r["success"]]
        
        if not successful_runs:
            return {
                "success": False,
                "error": "No successful runs",
                "total_runs": len(self.results),
                "failed_runs": len(failed_runs)
            }
        
        # Basic metrics
        avg_duration = sum(r["duration_s"] for r in successful_runs) / len(successful_runs)
        avg_word_count = sum(r["word_count"] for r in successful_runs) / len(successful_runs)
        avg_sources = sum(r["sources_count"] for r in successful_runs) / len(successful_runs)
        avg_coverage = sum(r["coverage_score"] for r in successful_runs) / len(successful_runs)
        
        # Phase 2 specific metrics
        critic_success_rate = sum(1 for r in successful_runs if r.get("critic_success", False)) / len(successful_runs)
        avg_critic_score = sum(r.get("critic_score", 0) for r in successful_runs) / len(successful_runs)
        
        contradiction_detection_rate = sum(1 for r in successful_runs if r.get("contradiction_detection_active", False)) / len(successful_runs)
        avg_contradictions = sum(r.get("contradictions_found", 0) for r in successful_runs) / len(successful_runs)
        
        structural_extraction_rate = sum(1 for r in successful_runs if r.get("structural_extraction_active", False)) / len(successful_runs)
        avg_structural_features = sum(r.get("structural_features_found", 0) for r in successful_runs) / len(successful_runs)
        
        multi_provider_effective_rate = sum(1 for r in successful_runs if r.get("multi_provider_effective", False)) / len(successful_runs)
        avg_source_diversity = sum(r.get("source_diversity_score", 0) for r in successful_runs) / len(successful_runs)
        
        audience_adaptation_rate = sum(1 for r in successful_runs if r.get("audience_match_detected", False)) / len(successful_runs)
        avg_audience_score = sum(r.get("audience_adaptation_score", 0) for r in successful_runs) / len(successful_runs)
        
        mode_effectiveness_rate = sum(1 for r in successful_runs if r.get("mode_target_met", False)) / len(successful_runs)
        avg_mode_score = sum(r.get("mode_effectiveness_score", 0) for r in successful_runs) / len(successful_runs)
        
        # Performance by research mode
        mode_performance = {}
        research_modes = set(r.get("research_mode") for r in successful_runs)
        for mode in research_modes:
            mode_runs = [r for r in successful_runs if r.get("research_mode") == mode]
            if mode_runs:
                mode_performance[mode] = {
                    "runs": len(mode_runs),
                    "avg_duration": sum(r["duration_s"] for r in mode_runs) / len(mode_runs),
                    "avg_word_count": sum(r["word_count"] for r in mode_runs) / len(mode_runs),
                    "success_rate": len(mode_runs) / len([r for r in self.results if r.get("research_mode") == mode])
                }
        
        # Performance by audience
        audience_performance = {}
        audiences = set(r.get("target_audience") for r in successful_runs)
        for audience in audiences:
            audience_runs = [r for r in successful_runs if r.get("target_audience") == audience]
            if audience_runs:
                audience_performance[audience] = {
                    "runs": len(audience_runs),
                    "avg_adaptation_score": sum(r.get("audience_adaptation_score", 0) for r in audience_runs) / len(audience_runs),
                    "adaptation_rate": sum(1 for r in audience_runs if r.get("audience_match_detected", False)) / len(audience_runs)
                }
        
        return {
            "success": True,
            "total_runs": len(self.results),
            "successful_runs": len(successful_runs),
            "failed_runs": len(failed_runs),
            "success_rate": len(successful_runs) / len(self.results) * 100,
            "total_duration_s": total_duration,
            
            # Basic metrics
            "avg_duration_s": avg_duration,
            "avg_word_count": avg_word_count,
            "avg_sources_count": avg_sources,
            "avg_coverage_score": avg_coverage,
            
            # Phase 2 Agent Intelligence metrics
            "critic_success_rate": critic_success_rate * 100,
            "avg_critic_score": avg_critic_score,
            "contradiction_detection_rate": contradiction_detection_rate * 100,
            "avg_contradictions_found": avg_contradictions,
            "structural_extraction_rate": structural_extraction_rate * 100,
            "avg_structural_features": avg_structural_features,
            "multi_provider_effective_rate": multi_provider_effective_rate * 100,
            "avg_source_diversity": avg_source_diversity,
            "audience_adaptation_rate": audience_adaptation_rate * 100,
            "avg_audience_adaptation_score": avg_audience_score,
            "mode_effectiveness_rate": mode_effectiveness_rate * 100,
            "avg_mode_effectiveness_score": avg_mode_score,
            
            # Detailed breakdowns
            "mode_performance": mode_performance,
            "audience_performance": audience_performance,
            "results": self.results
        }
    
    def _save_results(self, evaluation_summary: Dict[str, Any]):
        """Save evaluation results to file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = f"eval/phase2_results_{timestamp}.json"
            
            os.makedirs(os.path.dirname(results_file), exist_ok=True)
            
            with open(results_file, 'w') as f:
                json.dump(evaluation_summary, f, indent=2, default=str)
            
            print(f"💾 Phase 2 results saved to: {results_file}")
        
        except Exception as e:
            print(f"⚠️  Could not save results: {e}")
    
    def _print_phase2_summary(self, summary: Dict[str, Any]):
        """Print comprehensive Phase 2 evaluation summary."""
        print(f"\n{'='*60}")
        print("📊 PHASE 2 AGENT INTELLIGENCE EVALUATION SUMMARY")
        print("=" * 60)
        
        if not summary["success"]:
            print(f"❌ Evaluation failed: {summary.get('error')}")
            return
        
        # Basic results
        print(f"Runs Completed: {summary['total_runs']}")
        print(f"Success Rate: {summary['success_rate']:.1f}% ({summary['successful_runs']}/{summary['total_runs']})")
        print(f"Total Duration: {summary['total_duration_s']:.1f}s")
        
        if summary['successful_runs'] > 0:
            print(f"Average Duration: {summary['avg_duration_s']:.1f}s per run")
            print(f"Average Word Count: {summary['avg_word_count']:.0f} words")
            print(f"Average Sources: {summary['avg_sources_count']:.1f} sources")
            print(f"Average Coverage: {summary['avg_coverage_score']:.1%}")
            
            # Phase 2 specific metrics
            print(f"\n🤖 PHASE 2 AGENT INTELLIGENCE METRICS:")
            print(f"Critic Success Rate: {summary['critic_success_rate']:.1f}%")
            print(f"Average Critic Score: {summary['avg_critic_score']:.1f}/10")
            print(f"Contradiction Detection Rate: {summary['contradiction_detection_rate']:.1f}%")
            print(f"Structural Extraction Rate: {summary['structural_extraction_rate']:.1f}%")
            print(f"Multi-Provider Effective Rate: {summary['multi_provider_effective_rate']:.1f}%")
            print(f"Audience Adaptation Rate: {summary['audience_adaptation_rate']:.1f}%")
            print(f"Mode Effectiveness Rate: {summary['mode_effectiveness_rate']:.1f}%")
            
            # Research mode performance
            print(f"\n📊 RESEARCH MODE PERFORMANCE:")
            for mode, perf in summary.get('mode_performance', {}).items():
                print(f"  {mode}:")
                print(f"    Runs: {perf['runs']}, Success: {perf['success_rate']:.1%}")
                print(f"    Avg Duration: {perf['avg_duration']:.1f}s")
                print(f"    Avg Words: {perf['avg_word_count']:.0f}")
            
            # Audience performance
            print(f"\n👥 AUDIENCE ADAPTATION PERFORMANCE:")
            for audience, perf in summary.get('audience_performance', {}).items():
                print(f"  {audience}:")
                print(f"    Runs: {perf['runs']}, Adaptation Rate: {perf['adaptation_rate']:.1%}")
                print(f"    Avg Adaptation Score: {perf['avg_adaptation_score']:.2f}")
        
        # Print individual results summary
        print(f"\n📋 Individual Results Summary:")
        mode_counts = {}
        audience_counts = {}
        
        for result in summary['results']:
            mode = result.get('research_mode', 'Unknown')
            audience = result.get('target_audience', 'Unknown')
            
            mode_counts[mode] = mode_counts.get(mode, 0) + 1
            audience_counts[audience] = audience_counts.get(audience, 0) + 1
            
            status = "✅" if result["success"] else "❌"
            topic = result["topic"][:40] + "..." if len(result["topic"]) > 40 else result["topic"]
            
            if result["success"]:
                critic_score = result.get('critic_score', 0)
                contradictions = result.get('contradictions_found', 0)
                features = result.get('structural_features_found', 0)
                
                print(f"{status} {topic}")
                print(f"     Mode: {mode} → {audience}")
                print(f"     Duration: {result['duration_s']:.1f}s, Words: {result['word_count']}")
                print(f"     Critic: {critic_score:.1f}/10, Contradictions: {contradictions}, Features: {features}")
            else:
                print(f"{status} {topic}")
                print(f"     Mode: {mode} → {audience}")
                print(f"     Error: {result.get('error', 'Unknown error')}")


async def main():
    """Main Phase 2 evaluation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Nova Brief Phase 2 Agent Intelligence Evaluation")
    parser.add_argument("--quick", action="store_true", help="Run quick evaluation")
    parser.add_argument("--max-topics", type=int, help="Maximum number of topics to evaluate")
    parser.add_argument("--topics-file", default="eval/topics.json", help="Topics file path")
    parser.add_argument("--modes", nargs="+", help="Research modes to test")
    parser.add_argument("--audiences", nargs="+", help="Target audiences to test")
    
    args = parser.parse_args()
    
    # Validate environment
    if not validate_environment():
        print("❌ Environment validation failed. Please check configuration.")
        return False
    
    # Run Phase 2 evaluation
    harness = Phase2EvaluationHarness(args.topics_file)
    
    try:
        summary = await harness.run_phase2_evaluation(
            quick=args.quick,
            max_topics=args.max_topics,
            test_modes=args.modes,
            test_audiences=args.audiences
        )
        
        # Determine exit code based on Phase 2 metrics
        if summary["success"]:
            success_rate = summary["success_rate"]
            critic_rate = summary.get("critic_success_rate", 0)
            adaptation_rate = summary.get("audience_adaptation_rate", 0)
            
            # Phase 2 success criteria
            if (success_rate >= 80 and critic_rate >= 70 and adaptation_rate >= 60):
                print("🎉 Phase 2 Evaluation PASSED - Excellent performance across all capabilities")
                return True
            elif (success_rate >= 70 and critic_rate >= 50 and adaptation_rate >= 40):
                print("⚠️  Phase 2 Evaluation PARTIAL - Good performance with some areas for improvement")
                return True
            else:
                print("❌ Phase 2 Evaluation FAILED - Performance below acceptable thresholds")
                return False
        else:
            print("❌ Phase 2 Evaluation FAILED - Could not complete")
            return False
    
    except Exception as e:
        print(f"❌ Phase 2 evaluation failed with exception: {e}")
        logger.error(f"Phase 2 evaluation harness failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)