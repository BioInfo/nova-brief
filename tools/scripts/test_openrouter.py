#!/usr/bin/env python3
"""Test script for OpenRouter client debugging."""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dotenv import load_dotenv
from src.providers.openrouter_client import OpenRouterClient, create_json_schema_format

# Load environment variables
load_dotenv()

async def test_basic_chat():
    """Test basic chat without structured output."""
    print("🧪 Testing basic OpenRouter chat...")
    
    client = OpenRouterClient()
    
    messages = [
        {"role": "system", "content": "You are a helpful research assistant."},
        {"role": "user", "content": "Write a brief summary about artificial intelligence in 2-3 sentences."}
    ]
    
    try:
        response = await client.chat(
            messages=messages,
            temperature=0.1,
            max_tokens=500
        )
        
        print(f"✅ Success: {response['success']}")
        print(f"📝 Content length: {len(response.get('content', ''))}")
        print(f"🎯 Content preview: {response.get('content', '')[:200]}...")
        print(f"📊 Metrics: {response.get('metrics', {})}")
        
        return response['success'] and bool(response.get('content'))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_structured_output():
    """Test structured output with JSON schema."""
    print("\n🔬 Testing structured output...")
    
    client = OpenRouterClient()
    
    # Simple schema for testing
    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "key_points": {
                "type": "array",
                "items": {"type": "string"}
            }
        },
        "required": ["summary", "key_points"],
        "additionalProperties": False
    }
    
    messages = [
        {"role": "system", "content": "You are a helpful research assistant. Respond only in valid JSON format."},
        {"role": "user", "content": "Summarize artificial intelligence trends in 2025. Provide a summary and 2-3 key points."}
    ]
    
    try:
        response = await client.chat(
            messages=messages,
            temperature=0.1,
            max_tokens=500,
            response_format=create_json_schema_format(schema)
        )
        
        print(f"✅ Success: {response['success']}")
        print(f"📝 Content length: {len(response.get('content', ''))}")
        print(f"🎯 Content preview: {response.get('content', '')[:300]}...")
        print(f"📊 Metrics: {response.get('metrics', {})}")
        
        # Try to parse JSON if content exists
        if response.get('content'):
            try:
                import json
                parsed = json.loads(response['content'])
                print(f"🎉 JSON parsing successful: {parsed}")
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON parsing failed: {e}")
        
        return response['success'] and bool(response.get('content'))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def test_analyst_simulation():
    """Test a more complex analyst-style prompt."""
    print("\n🔍 Testing analyst simulation...")
    
    client = OpenRouterClient()
    
    messages = [
        {
            "role": "system", 
            "content": "You are a research analyst. Extract key claims from the provided content."
        },
        {
            "role": "user", 
            "content": """
            Research Topic: AI in Agriculture 2025
            
            Source Content:
            === Source 1: Tech Review ===
            URL: https://example.com/ai-farming
            Content: AI-powered farming systems are expected to increase crop yields by 20-30% in 2025. 
            Precision agriculture using machine learning can optimize water usage and reduce pesticide application.
            
            Extract 1-2 specific claims from this content with confidence scores.
            """
        }
    ]
    
    try:
        response = await client.chat(
            messages=messages,
            temperature=0.1,
            max_tokens=1000
        )
        
        print(f"✅ Success: {response['success']}")
        print(f"📝 Content length: {len(response.get('content', ''))}")
        print(f"🎯 Full content:\n{response.get('content', '')}")
        print(f"📊 Metrics: {response.get('metrics', {})}")
        
        return response['success'] and bool(response.get('content'))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def main():
    """Run all tests."""
    print("🚀 Starting OpenRouter client tests...")
    
    # Check environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found in environment")
        return
    
    print(f"🔑 API Key present: {api_key[:10]}...{api_key[-4:]}")
    print(f"🌐 Base URL: {os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')}")
    print(f"🤖 Model: {os.getenv('MODEL', 'openai/gpt-oss-120b')}")
    
    results = []
    
    # Test 1: Basic chat
    results.append(await test_basic_chat())
    
    # Test 2: Structured output
    results.append(await test_structured_output())
    
    # Test 3: Analyst simulation
    results.append(await test_analyst_simulation())
    
    # Summary
    print("\n📋 Test Results Summary:")
    print(f"Basic Chat: {'✅ PASS' if results[0] else '❌ FAIL'}")
    print(f"Structured Output: {'✅ PASS' if results[1] else '❌ FAIL'}")
    print(f"Analyst Simulation: {'✅ PASS' if results[2] else '❌ FAIL'}")
    
    passed = sum(results)
    total = len(results)
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! OpenRouter client is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the debug output above for details.")

if __name__ == "__main__":
    asyncio.run(main())