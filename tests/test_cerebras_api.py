#!/usr/bin/env python3
"""
Test script to verify Cerebras API connectivity and JSON mode functionality.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

# Load environment variables
load_dotenv()
load_dotenv('.env.local')

def test_basic_api():
    """Test basic API connectivity"""
    api_key = os.getenv("CEREBRAS_API_KEY")
    base_url = os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1")
    model = os.getenv("MODEL", "gpt-oss-120b")
    
    print(f"🧪 Testing Cerebras API:")
    print(f"- API Key: {'✅ Set' if api_key else '❌ Missing'}")
    print(f"- Base URL: {base_url}")
    print(f"- Model: {model}")
    print()
    
    if not api_key:
        print("❌ CEREBRAS_API_KEY not found in environment")
        return False
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        # Basic test
        print("🔍 Testing basic chat completion...")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Say 'Hello World' - respond with exactly those two words only."}
            ],
            max_tokens=10,
            temperature=0
        )
        
        content = response.choices[0].message.content
        print(f"✅ Basic API works! Response: '{content}'")
        print(f"   Tokens used: {response.usage.total_tokens}")
        print()
        return True
        
    except Exception as e:
        print(f"❌ Basic API test failed: {e}")
        return False

def test_json_mode():
    """Test JSON mode functionality"""
    api_key = os.getenv("CEREBRAS_API_KEY")
    base_url = os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1")
    model = os.getenv("MODEL", "gpt-oss-120b")
    
    if not api_key:
        print("❌ Skipping JSON mode test - no API key")
        return False
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        print("🔍 Testing JSON mode...")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Respond only with valid JSON."},
                {"role": "user", "content": "Create a JSON object with two fields: 'greeting' (string) and 'number' (integer). Set greeting to 'Hello' and number to 42."}
            ],
            response_format={"type": "json_object"},
            max_tokens=100,
            temperature=0
        )
        
        content = response.choices[0].message.content
        print(f"Raw response: {repr(content)}")
        
        # Try to parse JSON
        try:
            parsed = json.loads(content)
            print(f"✅ JSON mode works! Parsed: {parsed}")
            print(f"   Tokens used: {response.usage.total_tokens}")
            return True
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            return False
        
    except Exception as e:
        print(f"❌ JSON mode test failed: {e}")
        return False

def test_structured_outputs():
    """Test structured outputs with schema"""
    api_key = os.getenv("CEREBRAS_API_KEY")
    base_url = os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1")
    model = os.getenv("MODEL", "gpt-oss-120b")
    
    if not api_key:
        print("❌ Skipping structured outputs test - no API key")
        return False
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        print("🔍 Testing structured outputs...")
        
        # Define schema for research plan
        research_schema = {
            "type": "object",
            "properties": {
                "research_plan": {
                    "type": "object",
                    "properties": {
                        "main_topic": {"type": "string"},
                        "sub_questions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "question": {"type": "string"},
                                    "search_queries": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                },
                                "required": ["question", "search_queries"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["main_topic", "sub_questions"],
                    "additionalProperties": False
                }
            },
            "required": ["research_plan"],
            "additionalProperties": False
        }
        
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a research planning assistant."},
                {"role": "user", "content": "Create a research plan for 'AI in healthcare'. Include 2 sub-questions with 2 search queries each."}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "research_plan",
                    "strict": True,
                    "schema": research_schema
                }
            },
            max_tokens=500,
            temperature=0
        )
        
        content = response.choices[0].message.content
        print(f"Raw response: {repr(content[:200])}...")
        
        # Try to parse JSON
        try:
            parsed = json.loads(content)
            print(f"✅ Structured outputs work! Schema validated.")
            print(f"   Main topic: {parsed['research_plan']['main_topic']}")
            print(f"   Sub-questions: {len(parsed['research_plan']['sub_questions'])}")
            print(f"   Tokens used: {response.usage.total_tokens}")
            return True
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Structured outputs test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Cerebras API Test Suite")
    print("=" * 50)
    
    tests = [
        ("Basic API", test_basic_api),
        ("JSON Mode", test_json_mode),
        ("Structured Outputs", test_structured_outputs)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} Test...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} test passed")
            else:
                print(f"❌ {test_name} test failed")
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
        
        print("-" * 30)
    
    print(f"\n🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Cerebras API is working correctly.")
    else:
        print("⚠️  Some tests failed. Check API configuration or connectivity.")

if __name__ == "__main__":
    main()