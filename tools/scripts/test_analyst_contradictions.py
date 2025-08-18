#!/usr/bin/env python3
"""Test script for enhanced Analyst agent with contradiction detection."""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.agent.analyst import analyze
from src.storage.models import Document, Chunk


async def test_analyst_contradictions():
    """Test the enhanced Analyst agent with contradiction detection."""
    
    print("🧪 Testing enhanced Analyst agent with contradiction detection...")
    
    # Create test data with potential contradictions (using proper TypedDict structure)
    documents: list[Document] = [
        {
            'url': 'https://example1.com',
            'title': 'AI Market Report 2024',
            'text': 'The global AI market is valued at $50 billion according to recent estimates from leading research firms. AI adoption is growing rapidly in enterprise sectors, with 60% of companies implementing AI solutions.',
            'content_type': 'text/html',
            'source_meta': {'domain': 'example1.com', 'fetch_time': '2024-01-01'}
        },
        {
            'url': 'https://example2.com',
            'title': 'Tech Industry Analysis',
            'text': 'Industry analysts report the AI market size at $75 billion, showing significant growth potential. Enterprise AI adoption continues to accelerate across industries, particularly in healthcare and finance.',
            'content_type': 'text/html',
            'source_meta': {'domain': 'example2.com', 'fetch_time': '2024-01-01'}
        }
    ]

    chunks: list[Chunk] = [
        {
            'doc_url': 'https://example1.com',
            'text': 'The global AI market is valued at $50 billion according to recent estimates from leading research firms.',
            'hash': 'hash1',
            'tokens': 19,
            'chunk_index': 0
        },
        {
            'doc_url': 'https://example2.com',
            'text': 'Industry analysts report the AI market size at $75 billion, showing significant growth potential.',
            'hash': 'hash2',
            'tokens': 16,
            'chunk_index': 0
        },
        {
            'doc_url': 'https://example1.com',
            'text': 'AI adoption is growing rapidly in enterprise sectors, with 60% of companies implementing AI solutions.',
            'hash': 'hash3',
            'tokens': 16,
            'chunk_index': 1
        },
        {
            'doc_url': 'https://example2.com',
            'text': 'Enterprise AI adoption continues to accelerate across industries, particularly in healthcare and finance.',
            'hash': 'hash4',
            'tokens': 15,
            'chunk_index': 1
        }
    ]

    try:
        # Test the analysis function
        result = await analyze(
            documents=documents,
            chunks=chunks,
            sub_questions=[
                'What is the current AI market size?', 
                'How fast is AI adoption in enterprises?'
            ],
            topic='AI Market Analysis and Enterprise Adoption'
        )
        
        # Check results
        success = result.get("success", False)
        if not success:
            print(f"❌ Analysis failed: {result.get('error')}")
            return False
        
        claims = result.get("claims", [])
        contradictions = result.get("contradictions", [])
        supporting_clusters = result.get("supporting_clusters", [])
        citations = result.get("citations", [])
        
        print(f"✅ Analysis completed successfully")
        print(f"  📊 Claims extracted: {len(claims)}")
        print(f"  ⚡ Contradictions found: {len(contradictions)}")
        print(f"  🤝 Supporting clusters: {len(supporting_clusters)}")
        print(f"  📝 Citations created: {len(citations)}")
        
        # Show sample results
        if claims:
            print(f"\n📋 Sample claim:")
            sample_claim = claims[0]
            print(f"  Text: {sample_claim.get('text', 'N/A')}")
            print(f"  Type: {sample_claim.get('type', 'N/A')}")
            print(f"  Confidence: {sample_claim.get('confidence', 0.0)}")
        
        if contradictions:
            print(f"\n⚡ Sample contradiction:")
            sample_contradiction = contradictions[0]
            print(f"  Description: {sample_contradiction.get('description', 'N/A')}")
            print(f"  Details: {sample_contradiction.get('details', 'N/A')}")
            print(f"  Claim IDs: {sample_contradiction.get('claim_ids', [])}")
        
        if supporting_clusters:
            print(f"\n🤝 Sample supporting cluster:")
            sample_cluster = supporting_clusters[0]
            print(f"  Topic: {sample_cluster.get('topic', 'N/A')}")
            print(f"  Confidence: {sample_cluster.get('confidence', 0.0)}")
            print(f"  Source count: {sample_cluster.get('source_count', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the test."""
    try:
        success = asyncio.run(test_analyst_contradictions())
        print(f"\n🏁 Test Result: {'PASSED ✅' if success else 'FAILED ❌'}")
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())