#!/usr/bin/env python3
"""Test script to verify writer module fixes for empty response handling."""

import asyncio
import sys
import os
from typing import Dict, List, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from agent.writer import write, _generate_report_content, _retry_with_simple_prompt
from storage.models import Claim, Citation
from observability.logging import get_logger

logger = get_logger(__name__)


def create_sample_claims() -> List[Claim]:
    """Create sample claims for testing."""
    return [
        {
            "text": "AI diagnostic accuracy has improved by 15% in 2023-2024",
            "type": "fact",
            "confidence": 0.9,
            "source_urls": ["https://example.com/ai-diagnostics-1"],
            "context": "Healthcare AI diagnostics",
            "created_at": "2024-08-17T23:00:00Z"
        },
        {
            "text": "Machine learning models show 95% accuracy in radiology",
            "type": "fact", 
            "confidence": 0.85,
            "source_urls": ["https://example.com/radiology-ml"],
            "context": "Radiology AI performance",
            "created_at": "2024-08-17T23:00:00Z"
        },
        {
            "text": "Clinical decision support systems reduce errors by 20%",
            "type": "estimate",
            "confidence": 0.75,
            "source_urls": ["https://example.com/clinical-ai"],
            "context": "Clinical AI systems",
            "created_at": "2024-08-17T23:00:00Z"
        }
    ]


def create_sample_citations() -> List[Citation]:
    """Create sample citations for testing."""
    return [
        {
            "urls": ["https://example.com/ai-diagnostics-1"],
            "context": "AI diagnostic accuracy study",
            "created_at": "2024-08-17T23:00:00Z"
        },
        {
            "urls": ["https://example.com/radiology-ml"],
            "context": "Radiology ML performance research",
            "created_at": "2024-08-17T23:00:00Z"
        },
        {
            "urls": ["https://example.com/clinical-ai"],
            "context": "Clinical AI impact analysis",
            "created_at": "2024-08-17T23:00:00Z"
        }
    ]


async def test_writer_module():
    """Test the writer module with sample data."""
    print("🧪 Testing Writer Module Error Handling")
    print("=" * 50)
    
    # Create test data
    claims = create_sample_claims()
    citations = create_sample_citations()
    draft_sections = [
        "Introduction",
        "AI Diagnostic Accuracy Improvements", 
        "Machine Learning in Radiology",
        "Clinical Decision Support Systems",
        "Conclusion"
    ]
    topic = "Impact of artificial intelligence on diagnostic accuracy in healthcare 2023-2024"
    sub_questions = [
        "How has AI improved diagnostic accuracy?",
        "What are the key performance metrics?",
        "What challenges remain?"
    ]
    
    print(f"📋 Topic: {topic}")
    print(f"📊 Claims: {len(claims)}")
    print(f"📚 Citations: {len(citations)}")
    print(f"📝 Draft sections: {len(draft_sections)}")
    print()
    
    try:
        print("🚀 Starting report generation...")
        result = await write(
            claims=claims,
            citations=citations,
            draft_sections=draft_sections,
            topic=topic,
            sub_questions=sub_questions
        )
        
        if result["success"]:
            print("✅ Report generation successful!")
            print(f"📄 Report length: {len(result['report_md'])} characters")
            print(f"📖 Word count: {result.get('metadata', {}).get('word_count', 0)} words")
            print(f"🔗 References: {len(result.get('references', []))}")
            print()
            print("📝 Report preview (first 500 chars):")
            print("-" * 40)
            print(result['report_md'][:500] + "..." if len(result['report_md']) > 500 else result['report_md'])
            print("-" * 40)
            return True
        else:
            print(f"❌ Report generation failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"💥 Test exception: {e}")
        logger.error(f"Writer test failed: {e}")
        return False


async def test_fallback_mechanism():
    """Test the fallback mechanism specifically."""
    print("\n🔄 Testing Fallback Mechanisms")
    print("=" * 50)
    
    # Create minimal test data for fallback testing
    claims = create_sample_claims()[:2]  # Reduced for fallback test
    citations = create_sample_citations()[:2]
    
    from agent.writer import _organize_claims_for_writing, _create_citation_mapping
    
    organized_claims = _organize_claims_for_writing(claims)
    citation_map, references = _create_citation_mapping(citations)
    
    topic = "AI Healthcare Impact Test"
    sub_questions = ["How effective is AI in healthcare?"]
    
    print("🔄 Testing simple prompt fallback...")
    try:
        result = await _retry_with_simple_prompt(
            topic=topic,
            sub_questions=sub_questions,
            organized_claims=organized_claims,
            citation_map=citation_map
        )
        
        if result["success"]:
            print("✅ Fallback mechanism working!")
            print(f"📄 Fallback content length: {len(result['report_markdown'])} characters")
            return True
        else:
            print(f"❌ Fallback failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"💥 Fallback test exception: {e}")
        return False


async def main():
    """Run all writer tests."""
    print("🧪 Writer Module Fix Verification")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 2
    
    # Test 1: Main writer function
    if await test_writer_module():
        tests_passed += 1
    
    # Test 2: Fallback mechanism
    if await test_fallback_mechanism():
        tests_passed += 1
    
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Writer fixes are working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the logs for details.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)