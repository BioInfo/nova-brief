#!/usr/bin/env python3
"""Test script for analyst JSON parsing fix."""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dotenv import load_dotenv
from src.providers.openrouter_client import OpenRouterClient

# Load environment variables
load_dotenv()

async def test_analyst_json_parsing():
    """Test JSON parsing with the updated analyst prompt."""
    print("🧪 Testing analyst JSON parsing...")
    
    client = OpenRouterClient()
    
    # Use the same system prompt as analyst
    system_prompt = """You are a research analyst expert at synthesizing information from multiple sources. Your task is to:

1. Extract precise, verifiable claims from the provided content
2. Classify each claim as fact, estimate, or opinion
3. Assign confidence scores (0.0-1.0) based on evidence quality
4. Associate claims with their supporting source URLs
5. Identify areas needing additional research

Guidelines:
- Focus on specific, verifiable statements rather than general observations
- Prefer claims that can be backed by authoritative sources
- Mark estimates and opinions appropriately
- Higher confidence for facts from credible sources, lower for opinions
- Include diverse perspectives when available
- Flag claims that need stronger evidence

CRITICAL: You MUST respond with ONLY a valid JSON object in this exact format, with no additional text:
{
  "claims": [
    {
      "text": "specific verifiable claim",
      "type": "fact",
      "confidence": 0.85,
      "source_urls": ["https://example.com"]
    }
  ],
  "sections": ["Key Theme 1", "Key Theme 2"]
}

Do not include any text before or after the JSON. Only valid JSON."""

    user_prompt = """Research Topic: AI in Agriculture 2025

Sub-questions to address:
- How is AI improving crop yields?
- What are the latest AI farming technologies?

Source Content:

=== Source 1: Tech Review ===
URL: https://techreview.com/ai-farming-2025
Content: AI-powered precision agriculture systems are revolutionizing farming practices in 2025. Machine learning algorithms can now predict optimal planting times with 95% accuracy, leading to increased crop yields of 20-30%. Smart irrigation systems powered by AI reduce water consumption by up to 40% while maintaining crop health. Computer vision technology helps farmers detect crop diseases early, preventing widespread damage.

=== Source 2: Agriculture Journal ===
URL: https://agjournal.com/future-farming
Content: The integration of artificial intelligence in modern agriculture represents a paradigm shift towards sustainable farming. AI-driven soil analysis provides farmers with precise nutrient recommendations, optimizing fertilizer use and reducing environmental impact. Autonomous farming equipment, guided by AI navigation systems, can work 24/7 to plant and harvest crops with minimal human intervention.

Extract specific claims from this content, focusing on verifiable facts, estimates, and expert opinions. Associate each claim with its source URLs."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        response = await client.chat(
            messages=messages,
            temperature=0.1,
            max_tokens=1500
        )
        
        print(f"✅ API Success: {response['success']}")
        print(f"📝 Content length: {len(response.get('content', ''))}")
        
        content = response.get('content', '')
        if not content:
            print("❌ Empty content received")
            return False
        
        print(f"🎯 Raw response:\n{content}")
        
        # Test our JSON parsing logic
        import json
        import re
        
        json_content = content.strip()
        
        # Look for JSON object boundaries if there's extra text
        if not json_content.startswith('{'):
            print("📝 Response doesn't start with '{', looking for JSON...")
            json_match = re.search(r'\{.*\}', json_content, re.DOTALL)
            if json_match:
                json_content = json_match.group(0)
                print(f"🔍 Found JSON: {json_content[:100]}...")
            else:
                print("❌ No JSON object found in response")
                return False
        
        # Try parsing
        try:
            analysis_result = json.loads(json_content)
            claims = analysis_result.get("claims", [])
            sections = analysis_result.get("sections", [])
            
            print(f"🎉 JSON parsing successful!")
            print(f"📊 Claims found: {len(claims)}")
            print(f"📚 Sections found: {len(sections)}")
            
            # Display results
            for i, claim in enumerate(claims, 1):
                print(f"  Claim {i}: {claim.get('text', '')[:100]}...")
                print(f"    Type: {claim.get('type')}, Confidence: {claim.get('confidence')}")
            
            for i, section in enumerate(sections, 1):
                print(f"  Section {i}: {section}")
            
            return len(claims) > 0
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            print(f"🔍 Attempted to parse: {json_content[:200]}...")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    """Run the test."""
    print("🚀 Testing analyst JSON parsing fix...")
    
    # Check environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found in environment")
        return
    
    success = await test_analyst_json_parsing()
    
    if success:
        print("\n🎉 Test PASSED! Analyst JSON parsing is working correctly.")
    else:
        print("\n❌ Test FAILED! Analyst JSON parsing needs more work.")

if __name__ == "__main__":
    asyncio.run(main())