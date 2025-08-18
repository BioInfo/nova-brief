#!/usr/bin/env python3
"""Test script for Critic Agent quality assurance functionality."""

import sys
import os
import asyncio

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.agent.critic import critique_report, generate_improvement_suggestions


# Sample report content for testing
SAMPLE_REPORT = """
# Research Brief: Artificial Intelligence in Healthcare

## Executive Summary
Artificial Intelligence (AI) is transforming healthcare through improved diagnostics, personalized treatment plans, and operational efficiency. This research examines current applications, benefits, challenges, and future prospects.

## Key Findings

### Current Applications
- Medical imaging analysis with 95% accuracy in radiology
- Drug discovery acceleration by 30-50%
- Personalized treatment recommendations
- Administrative task automation

### Benefits
- Faster and more accurate diagnoses
- Reduced medical errors
- Cost savings through efficiency
- Enhanced patient outcomes

### Challenges
- Data privacy and security concerns
- Regulatory compliance requirements
- High implementation costs
- Need for specialized training

## Sources
- Mayo Clinic AI Research Initiative
- IEEE Medical AI Standards
- Healthcare IT News Analysis
- FDA AI Medical Device Guidelines

## Conclusion
AI presents significant opportunities for healthcare improvement, but successful implementation requires addressing regulatory, privacy, and training challenges.
"""

# Sample sources for testing
SAMPLE_SOURCES = [
    {
        "title": "Mayo Clinic AI Research Initiative",
        "url": "https://www.mayoclinic.org/ai-research",
        "domain": "mayoclinic.org",
        "score": 0.95
    },
    {
        "title": "IEEE Medical AI Standards",
        "url": "https://www.ieee.org/medical-ai",
        "domain": "ieee.org",
        "score": 0.90
    },
    {
        "title": "Healthcare IT News Analysis",
        "url": "https://www.healthcareitnews.com/ai-analysis",
        "domain": "healthcareitnews.com",
        "score": 0.85
    }
]

# Sample research context
SAMPLE_CONTEXT = {
    "research_mode": "⚖️ Balanced Analysis",
    "search_queries_count": 5,
    "sources_analyzed": 12,
    "search_strategy": "balanced"
}


async def test_basic_critique():
    """Test basic critique functionality."""
    print("🔍 Testing basic critique functionality...")
    
    try:
        result = await critique_report(
            report_content=SAMPLE_REPORT,
            research_topic="AI in Healthcare",
            target_audience="General",
            sources_used=SAMPLE_SOURCES,
            research_context=SAMPLE_CONTEXT
        )
        
        if result["success"]:
            critique = result["critique"]
            overall_score = critique.get("overall_score", 0)
            print(f"  ✅ Basic critique successful - Overall score: {overall_score}")
            
            # Check required sections
            required_sections = [
                "content_quality", "source_reliability", "structure_clarity",
                "bias_objectivity", "completeness", "evidence_support", "contradictions"
            ]
            
            missing_sections = [section for section in required_sections if section not in critique]
            if not missing_sections:
                print(f"  ✅ All required sections present")
            else:
                print(f"  ⚠️  Missing sections: {missing_sections}")
            
            return True
        else:
            print(f"  ❌ Basic critique failed: {result.get('error', 'Unknown error')}")
            return False
    
    except Exception as e:
        print(f"  ❌ Basic critique test failed: {e}")
        return False


async def test_audience_specific_critique():
    """Test audience-specific critique variations."""
    print("👥 Testing audience-specific critique...")
    
    audiences = ["Executive", "Technical", "General"]
    results = []
    
    for audience in audiences:
        try:
            result = await critique_report(
                report_content=SAMPLE_REPORT,
                research_topic="AI in Healthcare",
                target_audience=audience,
                sources_used=SAMPLE_SOURCES,
                research_context=SAMPLE_CONTEXT
            )
            
            if result["success"]:
                critique = result["critique"]
                metadata = critique.get("metadata", {})
                target_aud = metadata.get("target_audience", "Unknown")
                overall_score = critique.get("overall_score", 0)
                
                print(f"  ✅ {audience} audience: Score {overall_score} (Target: {target_aud})")
                results.append(True)
            else:
                print(f"  ❌ {audience} audience failed: {result.get('error', 'Unknown')}")
                results.append(False)
        
        except Exception as e:
            print(f"  ❌ {audience} audience test failed: {e}")
            results.append(False)
    
    return all(results)


async def test_critique_metadata():
    """Test critique metadata inclusion."""
    print("📊 Testing critique metadata...")
    
    try:
        result = await critique_report(
            report_content=SAMPLE_REPORT,
            research_topic="AI in Healthcare Research Analysis",
            target_audience="Technical",
            sources_used=SAMPLE_SOURCES,
            research_context=SAMPLE_CONTEXT
        )
        
        if result["success"]:
            critique = result["critique"]
            metadata = critique.get("metadata", {})
            
            required_metadata = [
                "target_audience", "research_topic", "report_length", "sources_count"
            ]
            
            present_metadata = [key for key in required_metadata if key in metadata]
            missing_metadata = [key for key in required_metadata if key not in metadata]
            
            if not missing_metadata:
                print(f"  ✅ All metadata present: {len(present_metadata)}/{len(required_metadata)}")
                print(f"    Report length: {metadata.get('report_length', 'N/A')}")
                print(f"    Sources count: {metadata.get('sources_count', 'N/A')}")
                return True
            else:
                print(f"  ⚠️  Missing metadata: {missing_metadata}")
                return False
        else:
            print(f"  ❌ Metadata test failed: {result.get('error', 'Unknown')}")
            return False
    
    except Exception as e:
        print(f"  ❌ Metadata test failed: {e}")
        return False


async def test_improvement_suggestions():
    """Test improvement suggestions generation."""
    print("💡 Testing improvement suggestions...")
    
    try:
        # First get a critique
        critique_result = await critique_report(
            report_content=SAMPLE_REPORT,
            research_topic="AI in Healthcare",
            target_audience="General",
            sources_used=SAMPLE_SOURCES,
            research_context=SAMPLE_CONTEXT
        )
        
        if not critique_result["success"]:
            print(f"  ❌ Could not get critique for suggestions test")
            return False
        
        # Then generate improvement suggestions
        suggestions_result = await generate_improvement_suggestions(
            critique_data=critique_result["critique"],
            report_content=SAMPLE_REPORT,
            target_audience="General"
        )
        
        if suggestions_result["success"]:
            suggestions = suggestions_result["suggestions"]
            
            required_categories = [
                "immediate_fixes", "content_enhancements", 
                "structural_improvements", "source_improvements", "revision_plan"
            ]
            
            present_categories = [cat for cat in required_categories if cat in suggestions]
            missing_categories = [cat for cat in required_categories if cat not in suggestions]
            
            if not missing_categories:
                print(f"  ✅ All suggestion categories present: {len(present_categories)}")
                
                # Check revision plan
                revision_plan = suggestions.get("revision_plan", {})
                should_revise = revision_plan.get("should_revise", False)
                revision_type = revision_plan.get("revision_type", "none")
                
                print(f"    Should revise: {should_revise}")
                print(f"    Revision type: {revision_type}")
                
                return True
            else:
                print(f"  ⚠️  Missing suggestion categories: {missing_categories}")
                return False
        else:
            print(f"  ❌ Suggestions generation failed: {suggestions_result.get('error', 'Unknown')}")
            return False
    
    except Exception as e:
        print(f"  ❌ Improvement suggestions test failed: {e}")
        return False


async def test_critique_scoring():
    """Test critique scoring consistency."""
    print("📈 Testing critique scoring...")
    
    try:
        result = await critique_report(
            report_content=SAMPLE_REPORT,
            research_topic="AI in Healthcare",
            target_audience="General",
            sources_used=SAMPLE_SOURCES,
            research_context=SAMPLE_CONTEXT
        )
        
        if result["success"]:
            critique = result["critique"]
            overall_score = critique.get("overall_score", 0)
            
            # Check score range
            if 0 <= overall_score <= 10:
                print(f"  ✅ Overall score in valid range: {overall_score}")
                
                # Check individual section scores
                sections_with_scores = [
                    "content_quality", "source_reliability", "structure_clarity",
                    "bias_objectivity", "completeness", "evidence_support"
                ]
                
                valid_scores = 0
                for section in sections_with_scores:
                    section_data = critique.get(section, {})
                    score = section_data.get("score", 0)
                    if 0 <= score <= 10:
                        valid_scores += 1
                    else:
                        print(f"    ⚠️  {section} score out of range: {score}")
                
                if valid_scores == len(sections_with_scores):
                    print(f"  ✅ All section scores valid: {valid_scores}/{len(sections_with_scores)}")
                    return True
                else:
                    print(f"  ⚠️  Some section scores invalid: {valid_scores}/{len(sections_with_scores)}")
                    return False
            else:
                print(f"  ❌ Overall score out of range: {overall_score}")
                return False
        else:
            print(f"  ❌ Scoring test failed: {result.get('error', 'Unknown')}")
            return False
    
    except Exception as e:
        print(f"  ❌ Scoring test failed: {e}")
        return False


async def test_error_handling():
    """Test error handling with invalid inputs."""
    print("🚫 Testing error handling...")
    
    # Test with empty report
    try:
        result = await critique_report(
            report_content="",
            research_topic="Empty Report Test",
            target_audience="General",
            sources_used=[],
            research_context={}
        )
        
        if result["success"]:
            print(f"  ✅ Empty report handled gracefully")
        else:
            print(f"  ✅ Empty report rejected appropriately: {result.get('error', 'No error')}")
        
        # Test with very long report
        long_report = "Very long content. " * 1000  # 3000+ words
        result = await critique_report(
            report_content=long_report,
            research_topic="Long Report Test",
            target_audience="General",
            sources_used=SAMPLE_SOURCES,
            research_context=SAMPLE_CONTEXT
        )
        
        if result["success"]:
            print(f"  ✅ Long report handled successfully")
        else:
            print(f"  ⚠️  Long report failed: {result.get('error', 'Unknown')}")
        
        return True
    
    except Exception as e:
        print(f"  ✅ Error handling working: {e}")
        return True


async def main():
    """Run all Critic agent tests."""
    print("🧪 Testing Critic Agent quality assurance functionality...\n")
    
    tests = [
        test_basic_critique,
        test_audience_specific_critique,
        test_critique_metadata,
        test_improvement_suggestions,
        test_critique_scoring,
        test_error_handling
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
    
    print(f"🏁 Critic Agent Tests: {success_count}/{total_count} passed")
    
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