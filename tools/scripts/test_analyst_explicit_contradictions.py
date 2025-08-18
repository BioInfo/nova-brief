#!/usr/bin/env python3
"""Test script for explicit contradiction detection in Analyst agent."""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.agent.analyst import analyze
from src.storage.models import Document, Chunk


async def test_explicit_contradictions():
    """Test with more explicit contradictions."""
    
    print("🧪 Testing explicit contradiction detection...")
    
    # Create test data with very clear contradictions
    documents: list[Document] = [
        {
            'url': 'https://source1.com', 
            'title': 'Climate Report A', 
            'text': 'Global temperature has increased by 1.5°C since 1900. Sea levels are rising at 3.2mm per year.',
            'content_type': 'text/html',
            'source_meta': {'domain': 'source1.com', 'fetch_time': '2024-01-01'}
        },
        {
            'url': 'https://source2.com', 
            'title': 'Climate Report B', 
            'text': 'Global temperature has increased by 0.8°C since 1900. Sea levels are rising at 2.1mm per year.',
            'content_type': 'text/html',
            'source_meta': {'domain': 'source2.com', 'fetch_time': '2024-01-01'}
        }
    ]

    chunks: list[Chunk] = [
        {
            'doc_url': 'https://source1.com', 
            'text': 'Global temperature has increased by 1.5°C since 1900.',
            'hash': 'hash1',
            'tokens': 9,
            'chunk_index': 0
        },
        {
            'doc_url': 'https://source2.com', 
            'text': 'Global temperature has increased by 0.8°C since 1900.',
            'hash': 'hash2',
            'tokens': 9,
            'chunk_index': 0
        },
        {
            'doc_url': 'https://source1.com', 
            'text': 'Sea levels are rising at 3.2mm per year.',
            'hash': 'hash3',
            'tokens': 8,
            'chunk_index': 1
        },
        {
            'doc_url': 'https://source2.com', 
            'text': 'Sea levels are rising at 2.1mm per year.',
            'hash': 'hash4',
            'tokens': 8,
            'chunk_index': 1
        }
    ]

    try:
        # Test the analysis function
        result = await analyze(
            documents=documents,
            chunks=chunks,
            sub_questions=[
                'What is the temperature increase since 1900?', 
                'How fast are sea levels rising?'
            ],
            topic='Climate Change Data Analysis'
        )
        
        success = result.get("success", False)
        if not success:
            print(f"❌ Analysis failed: {result.get('error')}")
            return False
        
        claims = result.get("claims", [])
        contradictions = result.get("contradictions", [])
        supporting_clusters = result.get("supporting_clusters", [])
        
        print(f"✅ Analysis completed")
        print(f"  📊 Claims: {len(claims)}")
        print(f"  ⚡ Contradictions: {len(contradictions)}")
        print(f"  🤝 Supporting clusters: {len(supporting_clusters)}")
        
        # Show all claims
        for i, claim in enumerate(claims):
            print(f"  Claim {i+1}: {claim.get('text', '')[:80]}...")
        
        # Show contradictions
        for i, contradiction in enumerate(contradictions):
            print(f"  Contradiction {i+1}: {contradiction.get('description', '')}")
            print(f"    Details: {contradiction.get('details', '')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the test."""
    try:
        success = asyncio.run(test_explicit_contradictions())
        print(f"\n🏁 Explicit Contradiction Test: {'PASSED ✅' if success else 'FAILED ❌'}")
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())