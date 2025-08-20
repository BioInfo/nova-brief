"""
Test script for Phase 4 implementation - Self-Correcting Generation and Advanced Evaluation Loop.

This script tests the key components of Phase 4:
1. Unified quality rubric
2. Critic review function
3. LLM-as-Judge evaluation
4. PDF report generation
"""

import asyncio
import sys
import os
import json
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_rubric_import():
    """Test that the unified quality rubric can be imported and used."""
    print("🧪 Testing unified quality rubric...")
    
    try:
        from eval.rubric import (
            get_critic_prompts, get_judge_prompts, 
            format_critic_prompt, format_judge_prompt,
            calculate_overall_score
        )
        
        # Test critic prompts
        critic_prompts = get_critic_prompts()
        assert "system_prompt" in critic_prompts
        assert "user_template" in critic_prompts
        assert "is_publishable" in critic_prompts["system_prompt"]
        
        # Test judge prompts
        judge_prompts = get_judge_prompts()
        assert "system_prompt" in judge_prompts
        assert "user_template" in judge_prompts
        assert "comprehensiveness_score" in judge_prompts["system_prompt"]
        
        # Test prompt formatting
        test_topic = "Test topic"
        test_audience = "General"
        test_questions = ["What is AI?", "How does it work?"]
        test_report = "# Test Report\n\nThis is a test report."
        
        critic_prompt = format_critic_prompt(test_topic, test_audience, test_questions, test_report)
        assert test_topic in critic_prompt
        assert test_audience in critic_prompt
        
        judge_prompt = format_judge_prompt(test_questions, test_report)
        assert "What is AI?" in judge_prompt
        assert test_report in judge_prompt
        
        # Test score calculation
        overall_score = calculate_overall_score(0.8, 0.7, 0.9)
        assert 0.0 <= overall_score <= 1.0
        
        print("✅ Unified quality rubric tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Rubric test failed: {e}")
        return False


async def test_critic_review():
    """Test the new critic review function."""
    print("🧪 Testing critic review function...")
    
    try:
        from src.agent.critic import review
        
        # Mock state and report data
        test_state = {
            "topic": "Test AI Research",
            "sub_questions": ["What is AI?", "How does machine learning work?"],
            "target_audience": "General"
        }
        
        test_report = """# AI Research Report

## Introduction
Artificial Intelligence (AI) is a rapidly evolving field that focuses on creating intelligent machines.

## Machine Learning
Machine learning is a subset of AI that enables computers to learn without being explicitly programmed.

## Conclusion
AI has significant potential to transform various industries.
"""
        
        # Test the review function
        result = await review(
            draft_report=test_report,
            state=test_state,
            target_audience="General"
        )
        
        # Validate response structure
        assert result.get("success") is True
        assert "is_publishable" in result
        assert "revisions_needed" in result
        assert isinstance(result["is_publishable"], bool)
        assert isinstance(result["revisions_needed"], list)
        
        print(f"✅ Critic review test passed - publishable: {result['is_publishable']}")
        return True
        
    except Exception as e:
        print(f"❌ Critic review test failed: {e}")
        return False


async def test_judge_evaluation():
    """Test the LLM-as-Judge evaluation."""
    print("🧪 Testing LLM-as-Judge evaluation...")
    
    try:
        from eval.judge import score_report
        
        test_report = """# AI Research Report

## Introduction
Artificial Intelligence (AI) is a rapidly evolving field that focuses on creating intelligent machines capable of performing tasks that typically require human intelligence.

## Machine Learning Fundamentals
Machine learning is a subset of AI that enables computers to learn and improve from experience without being explicitly programmed. It uses algorithms to analyze data, identify patterns, and make predictions.

## Applications and Impact
AI applications span across healthcare, finance, transportation, and education, revolutionizing how we approach complex problems and decision-making processes.

## Conclusion
The future of AI holds immense potential for solving global challenges while requiring careful consideration of ethical implications and responsible development practices.
"""
        
        test_questions = [
            "What is artificial intelligence?",
            "How does machine learning work?",
            "What are the applications of AI?",
            "What are the future implications?"
        ]
        
        # Test the judge evaluation
        result = await score_report(
            report_markdown=test_report,
            sub_questions=test_questions
        )
        
        # Validate response structure
        expected_fields = [
            "comprehensiveness_score", "synthesis_score", "clarity_score",
            "overall_quality_score", "justification"
        ]
        
        for field in expected_fields:
            assert field in result, f"Missing field: {field}"
            if field.endswith("_score"):
                score = result[field]
                assert 0.0 <= score <= 1.0, f"Score {field} out of range: {score}"
        
        print(f"✅ Judge evaluation test passed - overall score: {result['overall_quality_score']:.3f}")
        return True
        
    except Exception as e:
        print(f"❌ Judge evaluation test failed: {e}")
        return False


def test_pdf_generation():
    """Test PDF report generation."""
    print("🧪 Testing PDF report generation...")
    
    try:
        from eval.report_generator import create_pdf_report, validate_eval_results
        
        # Create mock evaluation results
        mock_results = {
            "success": True,
            "total_topics": 2,
            "successful_topics": 2,
            "failed_topics": 0,
            "success_rate": 100.0,
            "results": [
                {
                    "topic": "AI in Healthcare",
                    "success": True,
                    "duration_s": 45.2,
                    "word_count": 850,
                    "sources_count": 5,
                    "comprehensiveness_score": 0.85,
                    "synthesis_score": 0.78,
                    "clarity_score": 0.82,
                    "overall_quality_score": 0.82,
                    "justification": "Well-structured report with good coverage"
                },
                {
                    "topic": "Climate Change Solutions",
                    "success": True,
                    "duration_s": 52.1,
                    "word_count": 920,
                    "sources_count": 7,
                    "comprehensiveness_score": 0.79,
                    "synthesis_score": 0.84,
                    "clarity_score": 0.88,
                    "overall_quality_score": 0.83,
                    "justification": "Excellent synthesis and clarity"
                }
            ]
        }
        
        # Validate results structure
        is_valid = validate_eval_results(mock_results)
        assert is_valid, "Mock results should be valid"
        
        # Test PDF creation
        test_pdf_path = "tests/test_report.pdf"
        create_pdf_report(mock_results, test_pdf_path)
        
        # Check if PDF was created
        assert os.path.exists(test_pdf_path), "PDF file should be created"
        
        # Check file size (should be non-zero)
        file_size = os.path.getsize(test_pdf_path)
        assert file_size > 1000, f"PDF file too small: {file_size} bytes"
        
        # Clean up
        os.remove(test_pdf_path)
        
        print("✅ PDF generation test passed")
        return True
        
    except Exception as e:
        print(f"❌ PDF generation test failed: {e}")
        return False


async def main():
    """Run all Phase 4 tests."""
    print("🚀 Starting Phase 4 Implementation Tests")
    print("=" * 50)
    
    tests = [
        ("Unified Quality Rubric", test_rubric_import),
        ("Critic Review Function", test_critic_review),
        ("LLM-as-Judge Evaluation", test_judge_evaluation),
        ("PDF Report Generation", test_pdf_generation),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                success = await test_func()
            else:
                success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Phase 4 tests passed!")
        return True
    else:
        print("⚠️  Some tests failed. Check implementation.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)