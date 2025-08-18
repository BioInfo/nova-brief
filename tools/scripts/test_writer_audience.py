#!/usr/bin/env python3
"""Test script for Writer agent audience customization."""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.agent.writer import write
from src.storage.models import Claim, Citation


async def test_writer_audiences():
    """Test Writer agent with different target audiences."""
    
    print("🧪 Testing Writer agent with audience customization...")
    
    # Create test data with proper TypedDict structure
    claims: list[Claim] = [
        {
            'id': 'claim1',
            'text': 'Artificial intelligence adoption in enterprises increased by 37% in 2024.',
            'type': 'fact',
            'confidence': 0.9,
            'source_urls': ['https://example1.com']
        },
        {
            'id': 'claim2',
            'text': 'Machine learning models require significant computational resources for training.',
            'type': 'fact',
            'confidence': 0.85,
            'source_urls': ['https://example2.com']
        }
    ]
    
    citations: list[Citation] = [
        {
            'claim_id': 'claim1',
            'urls': ['https://example1.com'],
            'citation_number': None
        },
        {
            'claim_id': 'claim2',
            'urls': ['https://example2.com'],
            'citation_number': None
        }
    ]
    
    draft_sections = ['Introduction', 'Current State', 'Technical Requirements', 'Conclusion']
    topic = 'Enterprise AI Adoption'
    sub_questions = ['What is the current state of AI adoption?', 'What are the technical requirements?']
    
    # Test all three audiences
    audiences = ['Executive', 'Technical', 'General']
    
    for audience in audiences:
        print(f"\n📝 Testing {audience} audience...")
        
        try:
            result = await write(
                claims=claims,
                citations=citations,
                draft_sections=draft_sections,
                topic=topic,
                sub_questions=sub_questions,
                target_audience=audience
            )
            
            if result.get('success'):
                report_md = result.get('report_md', '')
                word_count = len(report_md.split())
                
                print(f"  ✅ {audience} report generated successfully")
                print(f"  📊 Word count: {word_count}")
                print(f"  📄 Report preview: {report_md[:200]}...")
                
                # Show audience-specific characteristics
                if audience == 'Executive':
                    expected_range = (600, 800)
                elif audience == 'Technical':
                    expected_range = (1000, 1500)
                else:  # General
                    expected_range = (800, 1000)
                
                if expected_range[0] <= word_count <= expected_range[1]:
                    print(f"  🎯 Word count within target range: {expected_range[0]}-{expected_range[1]}")
                else:
                    print(f"  ⚠️  Word count outside target range: {expected_range[0]}-{expected_range[1]}")
                
            else:
                print(f"  ❌ {audience} report failed: {result.get('error')}")
                return False
            
        except Exception as e:
            print(f"  ❌ {audience} test failed: {e}")
            return False
    
    return True


def main():
    """Run the test."""
    try:
        success = asyncio.run(test_writer_audiences())
        print(f"\n🏁 Writer Audience Test: {'PASSED ✅' if success else 'FAILED ❌'}")
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())