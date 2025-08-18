#!/usr/bin/env python3
"""Test script for iterative and reflective Planner agent."""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.agent.planner import plan, refine_plan
from src.storage.models import create_default_constraints


async def test_initial_planning():
    """Test the initial planning functionality."""
    print("📋 Testing initial planning...")
    
    try:
        topic = "Artificial Intelligence in Healthcare"
        constraints = create_default_constraints()
        
        result = await plan(topic, constraints)
        
        if result.get('success'):
            sub_questions = result.get('sub_questions', [])
            queries = result.get('queries', [])
            
            print(f"  ✅ Initial planning successful")
            print(f"  📊 Sub-questions generated: {len(sub_questions)}")
            print(f"  🔍 Search queries generated: {len(queries)}")
            
            if sub_questions:
                print(f"  📝 Sample sub-question: {sub_questions[0]}")
            if queries:
                print(f"  🔎 Sample query: {queries[0]}")
            
            return result
        else:
            print(f"  ❌ Initial planning failed: {result.get('error')}")
            return None
    except Exception as e:
        print(f"  ❌ Initial planning test failed: {e}")
        return None


async def test_plan_refinement():
    """Test the plan refinement functionality."""
    print("🔄 Testing plan refinement...")
    
    try:
        # Start with initial plan
        initial_result = await test_initial_planning()
        if not initial_result:
            print("  ⚠️  Skipping refinement test - initial planning failed")
            return False
        
        # Simulate some research results
        topic = "Artificial Intelligence in Healthcare"
        original_sub_questions = initial_result.get('sub_questions', [])
        original_queries = initial_result.get('queries', [])
        
        # Mock claims found (simulating partial research results)
        claims_found = [
            {"text": "AI can improve diagnostic accuracy in medical imaging by up to 30%"},
            {"text": "Machine learning algorithms are being used for drug discovery"},
            {"text": "Healthcare AI market is expected to reach $45 billion by 2026"}
        ]
        
        # Mock search results
        search_results = [
            {"title": "AI in Medical Diagnosis", "snippet": "Recent advances in AI diagnostics"},
            {"title": "Healthcare AI Applications", "snippet": "Various AI applications in healthcare"}
        ]
        
        constraints = create_default_constraints()
        
        # Test refinement
        refinement_result = await refine_plan(
            original_topic=topic,
            original_sub_questions=original_sub_questions,
            original_queries=original_queries,
            claims_found=claims_found,
            search_results=search_results,
            constraints=constraints
        )
        
        if refinement_result.get('success'):
            gaps = refinement_result.get('gaps_identified', [])
            new_sub_questions = refinement_result.get('new_sub_questions', [])
            new_queries = refinement_result.get('new_queries', [])
            rationale = refinement_result.get('refinement_rationale', '')
            
            print(f"  ✅ Plan refinement successful")
            print(f"  🕳️  Gaps identified: {len(gaps)}")
            print(f"  📊 New sub-questions: {len(new_sub_questions)}")
            print(f"  🔍 New queries: {len(new_queries)}")
            
            if gaps:
                print(f"  🔍 Sample gap: {gaps[0]}")
            if new_sub_questions:
                print(f"  📝 Sample new question: {new_sub_questions[0]}")
            if new_queries:
                print(f"  🔎 Sample new query: {new_queries[0]}")
            if rationale:
                print(f"  💡 Rationale: {rationale[:100]}...")
            
            return True
        else:
            print(f"  ❌ Plan refinement failed: {refinement_result.get('error')}")
            return False
            
    except Exception as e:
        print(f"  ❌ Plan refinement test failed: {e}")
        return False


async def test_coverage_analysis():
    """Test the coverage analysis functionality."""
    print("📊 Testing coverage analysis...")
    
    try:
        from src.agent.planner import _analyze_coverage
        
        # Test data
        sub_questions = [
            "What are the main applications of AI in healthcare?",
            "What are the challenges of implementing AI in healthcare?",
            "What is the future of AI in healthcare?"
        ]
        
        claims_found = [
            {"text": "AI applications include medical imaging, drug discovery, and patient monitoring"},
            {"text": "Implementation challenges include data privacy and regulatory compliance"},
            {"text": "The healthcare AI market is growing rapidly"}
        ]
        
        search_results = [
            {"title": "AI Healthcare Applications", "snippet": "Medical imaging and diagnostics"},
            {"title": "Healthcare AI Challenges", "snippet": "Privacy and regulatory issues"}
        ]
        
        coverage = _analyze_coverage(sub_questions, claims_found, search_results)
        
        print(f"  ✅ Coverage analysis successful")
        print(f"  📈 Well-covered questions: {len(coverage.get('well_covered', []))}")
        print(f"  📉 Questions with gaps: {len(coverage.get('gaps', []))}")
        print(f"  🔍 Missing angles identified: {len(coverage.get('missing_angles', []))}")
        
        if coverage.get('missing_angles'):
            print(f"  🎯 Sample missing angle: {coverage['missing_angles'][0]}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Coverage analysis test failed: {e}")
        return False


async def main():
    """Run all iterative planner tests."""
    print("🧪 Testing iterative and reflective Planner agent...\n")
    
    tests = [
        test_initial_planning,
        test_plan_refinement,
        test_coverage_analysis
    ]
    
    results = []
    for test in tests:
        try:
            if test == test_initial_planning:
                # For initial planning, we already handle the return
                result = await test()
                results.append(result is not None)
            else:
                result = await test()
                results.append(result)
        except Exception as e:
            print(f"  ❌ Test execution failed: {e}")
            results.append(False)
        print()  # Add spacing between tests
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"🏁 Iterative Planner Tests: {success_count}/{total_count} passed")
    
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