#!/usr/bin/env python3
"""Test script for Phase 2 evaluation harness functionality."""

import sys
import os
import asyncio

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from eval.phase2_harness import Phase2EvaluationHarness


async def test_harness_initialization():
    """Test Phase 2 harness initialization."""
    print("🔧 Testing Phase 2 harness initialization...")
    
    try:
        harness = Phase2EvaluationHarness("eval/test_topics.json")
        
        if hasattr(harness, 'results') and hasattr(harness, 'topics_file'):
            print("  ✅ Harness initialized successfully")
            print(f"    Topics file: {harness.topics_file}")
            print(f"    Results list: {len(harness.results)} items")
            return True
        else:
            print("  ❌ Harness missing required attributes")
            return False
    
    except Exception as e:
        print(f"  ❌ Harness initialization failed: {e}")
        return False


async def test_topic_creation():
    """Test Phase 2 topic creation."""
    print("📝 Testing Phase 2 topic creation...")
    
    try:
        harness = Phase2EvaluationHarness("eval/test_topics.json")
        
        # Test topic creation
        topics = harness._create_phase2_topics()
        
        if topics and len(topics) > 0:
            print(f"  ✅ Created {len(topics)} Phase 2 topics")
            
            # Check topic structure
            first_topic = topics[0]
            required_fields = ["topic", "expected_elements"]
            
            if all(field in first_topic for field in required_fields):
                print("  ✅ Topics have required structure")
                print(f"    Sample topic: {first_topic['topic'][:50]}...")
                print(f"    Expected elements: {len(first_topic['expected_elements'])}")
                return True
            else:
                print("  ❌ Topics missing required fields")
                return False
        else:
            print("  ❌ No topics created")
            return False
    
    except Exception as e:
        print(f"  ❌ Topic creation failed: {e}")
        return False


async def test_metrics_calculation():
    """Test Phase 2 metrics calculation."""
    print("📊 Testing Phase 2 metrics calculation...")
    
    try:
        harness = Phase2EvaluationHarness("eval/test_topics.json")
        
        # Create mock results for testing
        mock_results = [
            {
                "success": True,
                "duration_s": 120.5,
                "word_count": 850,
                "sources_count": 6,
                "coverage_score": 0.8,
                "research_mode": "⚖️ Balanced Analysis",
                "target_audience": "General",
                "critic_success": True,
                "critic_score": 7.5,
                "contradictions_found": 2,
                "structural_features_found": 8,
                "source_diversity_score": 0.7,
                "audience_adaptation_score": 0.75,
                "mode_effectiveness_score": 0.85,
                # Include all required metrics
                "critic_should_revise": False,
                "critic_suggestions_count": 3,
                "critic_error": None,
                "supporting_clusters_found": 4,
                "contradiction_detection_active": True,
                "content_types_detected": 2,
                "content_types_list": ["academic", "news"],
                "structural_extraction_active": True,
                "source_domains_count": 4,
                "multi_provider_effective": True,
                "avg_sentence_length": 18.5,
                "technical_terms_count": 12,
                "executive_terms_count": 8,
                "audience_match_detected": True,
                "mode_constraints_followed": True,
                "mode_target_met": True
            },
            {
                "success": False,
                "duration_s": 45.2,
                "error": "Network timeout",
                "research_mode": "🚀 Quick Brief",
                "target_audience": "Executive",
                # Empty metrics
                "word_count": 0,
                "sources_count": 0,
                "coverage_score": 0.0,
                "critic_success": False,
                "critic_score": 0,
                "contradictions_found": 0,
                "structural_features_found": 0,
                "source_diversity_score": 0.0,
                "audience_adaptation_score": 0.0,
                "mode_effectiveness_score": 0.0
            }
        ]
        
        harness.results = mock_results
        
        # Test metrics calculation
        total_duration = 200.0
        metrics = harness._calculate_phase2_metrics(total_duration)
        
        if metrics["success"]:
            print("  ✅ Metrics calculation successful")
            print(f"    Success rate: {metrics['success_rate']:.1f}%")
            print(f"    Critic success rate: {metrics['critic_success_rate']:.1f}%")
            print(f"    Avg critic score: {metrics['avg_critic_score']:.1f}")
            print(f"    Mode performance entries: {len(metrics.get('mode_performance', {}))}")
            print(f"    Audience performance entries: {len(metrics.get('audience_performance', {}))}")
            return True
        else:
            print(f"  ❌ Metrics calculation failed: {metrics.get('error')}")
            return False
    
    except Exception as e:
        print(f"  ❌ Metrics calculation failed: {e}")
        return False


async def test_constraint_generation():
    """Test research mode constraint generation."""
    print("⚙️ Testing constraint generation...")
    
    try:
        harness = Phase2EvaluationHarness("eval/test_topics.json")
        
        # Test different research modes
        modes = ["🚀 Quick Brief", "⚖️ Balanced Analysis", "🔬 Deep Dive"]
        
        for mode in modes:
            constraints = harness._get_mode_constraints(mode, quick=False)
            
            if isinstance(constraints, dict) and "max_rounds" in constraints:
                print(f"  ✅ {mode}: {constraints['max_rounds']} rounds, {constraints.get('fetch_timeout_s', 'N/A')}s timeout")
            else:
                print(f"  ❌ {mode}: Invalid constraints structure")
                return False
        
        # Test quick mode
        quick_constraints = harness._get_mode_constraints("⚖️ Balanced Analysis", quick=True)
        if quick_constraints.get("max_rounds", 0) <= 1:
            print("  ✅ Quick mode constraints applied correctly")
        else:
            print("  ⚠️  Quick mode constraints may not be applied")
        
        return True
    
    except Exception as e:
        print(f"  ❌ Constraint generation failed: {e}")
        return False


async def test_empty_metrics():
    """Test empty metrics generation."""
    print("📋 Testing empty metrics generation...")
    
    try:
        harness = Phase2EvaluationHarness("eval/test_topics.json")
        
        empty_metrics = harness._empty_metrics()
        
        # Check if all required metrics are present with default values
        required_metrics = [
            "word_count", "sources_count", "claims_count", "citations_count",
            "coverage_score", "critic_success", "critic_score", "contradictions_found",
            "structural_features_found", "audience_adaptation_score", "mode_effectiveness_score"
        ]
        
        missing_metrics = [metric for metric in required_metrics if metric not in empty_metrics]
        
        if not missing_metrics:
            print(f"  ✅ All {len(required_metrics)} required metrics present")
            print(f"    Sample metrics: critic_score={empty_metrics['critic_score']}, word_count={empty_metrics['word_count']}")
            return True
        else:
            print(f"  ❌ Missing metrics: {missing_metrics}")
            return False
    
    except Exception as e:
        print(f"  ❌ Empty metrics test failed: {e}")
        return False


async def test_coverage_evaluation():
    """Test content coverage evaluation."""
    print("🎯 Testing content coverage evaluation...")
    
    try:
        harness = Phase2EvaluationHarness("eval/test_topics.json")
        
        # Test content and expected elements
        test_content = """
        This report covers artificial intelligence applications in healthcare.
        AI diagnostic tools have shown significant accuracy improvements.
        However, implementation challenges remain significant.
        Healthcare provider adoption varies across institutions.
        """
        
        expected_elements = [
            "AI diagnostic tools",
            "accuracy improvements", 
            "implementation challenges",
            "healthcare provider adoption",
            "missing element"  # This shouldn't be found
        ]
        
        coverage_score = harness._evaluate_content_coverage(test_content, expected_elements)
        
        # Should find 4 out of 5 elements
        expected_coverage = 4.0 / 5.0  # 0.8
        
        if 0.7 <= coverage_score <= 0.9:  # Allow some tolerance
            print(f"  ✅ Coverage evaluation successful: {coverage_score:.2f}")
            print(f"    Expected ~{expected_coverage:.2f}, got {coverage_score:.2f}")
            return True
        else:
            print(f"  ❌ Coverage evaluation unexpected: {coverage_score:.2f} (expected ~{expected_coverage:.2f})")
            return False
    
    except Exception as e:
        print(f"  ❌ Coverage evaluation failed: {e}")
        return False


async def main():
    """Run all Phase 2 harness tests."""
    print("🧪 Testing Phase 2 Agent Intelligence Evaluation Harness...\n")
    
    tests = [
        test_harness_initialization,
        test_topic_creation,
        test_metrics_calculation,
        test_constraint_generation,
        test_empty_metrics,
        test_coverage_evaluation
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"  ❌ Test execution failed: {e}")
            results.append(False)
        print()  # Add spacing between tests
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"🏁 Phase 2 Harness Tests: {success_count}/{total_count} passed")
    
    if success_count == total_count:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        exit(1)