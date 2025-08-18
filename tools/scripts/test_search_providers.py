#!/usr/bin/env python3
"""Test script for multi-provider search integration."""

import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.providers.search_providers import SearchManager, DuckDuckGoProvider, TavilyProvider


async def test_duckduckgo_provider():
    """Test DuckDuckGo provider."""
    print("🦆 Testing DuckDuckGo provider...")
    
    try:
        provider = DuckDuckGoProvider()
        results = await provider.search("artificial intelligence", max_results=3)
        
        print(f"  ✅ DuckDuckGo search successful: {len(results)} results")
        if results:
            print(f"  📄 Sample result: {results[0].title[:60]}...")
        return True
    except Exception as e:
        print(f"  ❌ DuckDuckGo test failed: {e}")
        return False


async def test_tavily_provider():
    """Test Tavily provider."""
    print("🔍 Testing Tavily provider...")
    
    try:
        provider = TavilyProvider()
        
        # Check if API key is available
        if not provider.api_key:
            print("  ⚠️  Tavily API key not available - skipping test")
            return True
        
        results = await provider.search("artificial intelligence", max_results=3)
        
        print(f"  ✅ Tavily search successful: {len(results)} results")
        if results:
            print(f"  📄 Sample result: {results[0].title[:60]}...")
        return True
    except Exception as e:
        print(f"  ❌ Tavily test failed: {e}")
        # Don't fail the overall test if Tavily is unavailable
        if "API key" in str(e) or "not available" in str(e):
            print("  ⚠️  Tavily API key issue - test skipped")
            return True
        return False


async def test_search_manager():
    """Test SearchManager with single provider."""
    print("🔧 Testing SearchManager...")
    
    try:
        manager = SearchManager()
        queries = ["AI research", "machine learning"]
        
        # Test with DuckDuckGo (should always be available)
        results = await manager.search(
            queries=queries,
            provider="duckduckgo",
            max_results_per_query=2
        )
        
        print(f"  ✅ SearchManager test successful: {len(results)} results")
        if results:
            print(f"  📄 Sample result: {results[0].title[:60]}...")
        return True
    except Exception as e:
        print(f"  ❌ SearchManager test failed: {e}")
        return False


async def test_multi_provider_search():
    """Test multi-provider search functionality."""
    print("🌐 Testing multi-provider search...")
    
    try:
        manager = SearchManager()
        queries = ["artificial intelligence"]
        
        # Test with available providers
        available_providers = []
        if "duckduckgo" in manager.providers:
            available_providers.append("duckduckgo")
        
        # Check if Tavily is available (has API key)
        if "tavily" in manager.providers:
            tavily_provider = manager.providers["tavily"]
            if tavily_provider.api_key:
                available_providers.append("tavily")
        
        if not available_providers:
            print("  ⚠️  No providers available for testing")
            return True
        
        print(f"  🔍 Testing with providers: {available_providers}")
        
        results = await manager.multi_provider_search(
            queries=queries,
            providers=available_providers,
            max_results_per_query=2
        )
        
        print(f"  ✅ Multi-provider search successful: {len(results)} results")
        
        # Show source diversity
        domains = set()
        for result in results:
            try:
                from urllib.parse import urlparse
                domain = urlparse(result.url).netloc
                domains.add(domain)
            except:
                pass
        
        print(f"  🌍 Source diversity: {len(domains)} unique domains")
        
        if results:
            print(f"  📄 Sample result: {results[0].title[:60]}...")
        
        return True
    except Exception as e:
        print(f"  ❌ Multi-provider test failed: {e}")
        return False


async def main():
    """Run all search provider tests."""
    print("🧪 Testing search provider integration...\n")
    
    tests = [
        test_duckduckgo_provider,
        test_tavily_provider,
        test_search_manager,
        test_multi_provider_search
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
    
    print(f"🏁 Search Provider Tests: {success_count}/{total_count} passed")
    
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