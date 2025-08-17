#!/usr/bin/env python3
"""
Test script to validate Cerebras provider routing for GPT-OSS-120B.
This tests actual API calls to ensure the routing headers work correctly.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from src.providers.openrouter_client import LLMClient


async def test_default_vs_cerebras_routing():
    """Test both default and Cerebras routing for GPT-OSS-120B."""
    print("🧪 TESTING CEREBRAS PROVIDER ROUTING")
    print("=" * 50)
    
    # Test messages
    test_messages = [
        {"role": "user", "content": "Say 'Hello from default routing' if you're using default routing, or 'Hello from Cerebras' if you're using Cerebras inference."}
    ]
    
    try:
        # Test 1: Default routing
        print("\n1️⃣ Testing GPT-OSS-120B with default routing...")
        client_default = LLMClient(model_key="gpt-oss-120b-openrouter-default")
        
        print(f"   Model: {client_default.model}")
        print(f"   Provider: {client_default.provider}")
        print(f"   Config: {client_default.model_config}")
        
        # Check headers (simulate what would be sent)
        headers = client_default.client.default_headers
        print(f"   Headers: {headers}")
        
        # Make actual API call
        print("   Making API call...")
        response_default = await client_default.chat(
            messages=test_messages,
            max_tokens=50,
            temperature=0.1
        )
        
        if response_default["success"]:
            print(f"   ✅ Default routing response: {response_default['content']}")
        else:
            print(f"   ❌ Default routing failed: {response_default['error']}")
        
        # Test 2: Cerebras routing
        print("\n2️⃣ Testing GPT-OSS-120B with Cerebras routing...")
        client_cerebras = LLMClient(model_key="gpt-oss-120b-openrouter-cerebras")
        
        print(f"   Model: {client_cerebras.model}")
        print(f"   Provider: {client_cerebras.provider}")
        print(f"   Config: {client_cerebras.model_config}")
        
        # Check headers
        headers = client_cerebras.client.default_headers
        print(f"   Headers: {headers}")
        
        # Verify Cerebras header is present
        if "X-OpenRouter-Provider" in headers:
            print(f"   🧠 Cerebras header detected: {headers['X-OpenRouter-Provider']}")
        else:
            print("   ⚠️ Cerebras header missing!")
        
        # Make actual API call
        print("   Making API call...")
        response_cerebras = await client_cerebras.chat(
            messages=test_messages,
            max_tokens=50,
            temperature=0.1
        )
        
        if response_cerebras["success"]:
            print(f"   ✅ Cerebras routing response: {response_cerebras['content']}")
        else:
            print(f"   ❌ Cerebras routing failed: {response_cerebras['error']}")
        
        # Compare responses
        print("\n🔍 COMPARISON:")
        if response_default["success"] and response_cerebras["success"]:
            print("   Both routing methods working successfully!")
            print(f"   Default: {response_default['content'][:100]}...")
            print(f"   Cerebras: {response_cerebras['content'][:100]}...")
            
            # Check metrics if available
            if "metrics" in response_default and "metrics" in response_cerebras:
                def_tokens = response_default["metrics"].get("total_tokens", 0)
                cer_tokens = response_cerebras["metrics"].get("total_tokens", 0)
                print(f"   Token usage - Default: {def_tokens}, Cerebras: {cer_tokens}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False


async def test_provider_header_logic():
    """Test that provider headers are correctly set."""
    print("\n🔧 TESTING PROVIDER HEADER LOGIC")
    print("=" * 50)
    
    # Test different configurations
    test_configs = [
        "gpt-oss-120b-openrouter-default",
        "gpt-oss-120b-openrouter-cerebras",
        "claude-sonnet-4-openrouter-default"
    ]
    
    for model_key in test_configs:
        try:
            client = LLMClient(model_key=model_key)
            headers = client.client.default_headers
            
            print(f"\n📋 {model_key}:")
            print(f"   Headers: {headers}")
            
            if "cerebras" in model_key:
                if "X-OpenRouter-Provider" in headers:
                    print(f"   ✅ Cerebras header present: {headers['X-OpenRouter-Provider']}")
                else:
                    print("   ❌ Cerebras header missing!")
            else:
                if "X-OpenRouter-Provider" not in headers:
                    print("   ✅ No provider header (default routing)")
                else:
                    print(f"   ⚠️ Unexpected provider header: {headers['X-OpenRouter-Provider']}")
                    
        except Exception as e:
            print(f"   ❌ Failed to initialize {model_key}: {e}")
    
    return True


async def main():
    """Run routing tests."""
    print("🚀 CEREBRAS ROUTING TEST SUITE")
    print("=" * 50)
    
    try:
        # Test header logic first
        await test_provider_header_logic()
        
        # Test actual API calls
        await test_default_vs_cerebras_routing()
        
        print("\n✅ ROUTING TESTS COMPLETED")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)