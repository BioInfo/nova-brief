#!/usr/bin/env python3
"""Test script to verify writer JSON parsing is working correctly."""

import sys
import os
import asyncio
import json
from typing import List

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.agent.writer import write
from src.storage.models import Claim, Citation

async def test_writer_json():
    """Test the writer component with sample claims and citations."""
    
    print("🧪 Testing Writer JSON Parsing...")
    
    # Sample claims (similar to what analyst would produce)
    sample_claims: List[Claim] = [
        {
            "id": "claim_1",
            "text": "AI-powered precision agriculture can increase crop yields by 10-15% through optimized planting patterns and resource allocation.",
            "type": "estimate",
            "confidence": 0.78,
            "source_urls": ["https://example.com/ai-agriculture-study"]
        },
        {
            "id": "claim_2",
            "text": "Machine learning algorithms can predict crop diseases 2-3 weeks before visible symptoms appear.",
            "type": "fact",
            "confidence": 0.85,
            "source_urls": ["https://example.com/disease-prediction-research"]
        },
        {
            "id": "claim_3",
            "text": "Drone-based monitoring systems are becoming essential tools for modern farming operations.",
            "type": "opinion",
            "confidence": 0.72,
            "source_urls": ["https://example.com/drone-farming-trends"]
        }
    ]
    
    # Sample citations
    sample_citations: List[Citation] = [
        {
            "claim_id": "claim_1",
            "urls": ["https://example.com/ai-agriculture-study"],
            "citation_number": None
        },
        {
            "claim_id": "claim_2",
            "urls": ["https://example.com/disease-prediction-research"],
            "citation_number": None
        },
        {
            "claim_id": "claim_3",
            "urls": ["https://example.com/drone-farming-trends"],
            "citation_number": None
        }
    ]
    
    # Sample data
    topic = "AI Improving Crop Yields"
    sub_questions = [
        "How does AI technology enhance agricultural productivity?",
        "What are the main AI applications in modern farming?",
        "What evidence exists for AI's impact on crop yield increases?"
    ]
    draft_sections = [
        "Introduction to AI in Agriculture",
        "Precision Agriculture Technologies", 
        "Predictive Analytics for Crops",
        "Future Implications"
    ]
    
    try:
        # Test the writer component
        result = await write(
            claims=sample_claims,
            citations=sample_citations,
            draft_sections=draft_sections,
            topic=topic,
            sub_questions=sub_questions
        )
        
        # Check if successful
        if result["success"]:
            report_md = result["report_md"]
            references = result["references"]
            metadata = result["metadata"]
            
            print("✅ Test PASSED! Writer JSON parsing is working correctly")
            print(f"📊 Report Stats:")
            print(f"   - Word count: {metadata['word_count']}")
            print(f"   - Citations: {metadata['citation_count']}")
            print(f"   - Sections: {len(metadata['sections'])}")
            print(f"   - Claims included: {metadata['claims_included']}")
            
            print(f"\n📝 Report Preview (first 300 chars):")
            print(f"   {report_md[:300]}...")
            
            print(f"\n🔗 References:")
            for ref in references[:3]:  # Show first 3 references
                print(f"   [{ref['number']}] {ref['url']}")
            
            return True
            
        else:
            print(f"❌ Test FAILED! Writer returned error: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test FAILED! Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the writer test."""
    print("🚀 Starting Writer Component Test...")
    
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Check for API key
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print("❌ OPENROUTER_API_KEY not found in environment")
            return
        
        print("✅ Environment setup complete")
        
        # Run the test
        success = await test_writer_json()
        
        if success:
            print("\n🎉 All tests passed! Writer component is working correctly.")
        else:
            print("\n💥 Tests failed! Check the output above for details.")
            
    except Exception as e:
        print(f"💥 Test setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())