#!/usr/bin/env python3
"""
Test script to verify the planner fix works with traditional JSON prompting.
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.agent.planner import plan

# Load environment variables
load_dotenv()
load_dotenv('.env.local')

async def test_planner():
    """Test the fixed planner"""
    print("🧪 Testing Fixed Planner")
    print("=" * 40)
    
    topic = "CRISPR gene editing ethical considerations"
    print(f"📋 Topic: {topic}")
    print()
    
    try:
        result = await plan(topic)
        
        if result["success"]:
            print("✅ Planning succeeded!")
            print(f"   Query count: {result['query_count']}")
            print(f"   Sub-questions: {len(result['research_plan'].get('sub_questions', []))}")
            print(f"   Tokens used: {result.get('tokens_used', 0)}")
            
            # Show the queries
            print(f"\n📝 Generated queries:")
            for i, query in enumerate(result['all_queries'][:3], 1):
                print(f"   {i}. {query}")
            
            print("\n🎉 Planner is working correctly!")
            return True
        else:
            print(f"❌ Planning failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Test crashed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_planner())
    if success:
        print("\n✅ Test passed - ready to test in Streamlit!")
    else:
        print("\n❌ Test failed - check configuration")