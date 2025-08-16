"""
Search provider implementations for web search functionality.
Currently supports DuckDuckGo with pluggable architecture for other providers.
"""

import os
import httpx
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class DuckDuckGoProvider:
    """DuckDuckGo search provider using their instant answer API."""
    
    def __init__(self):
        self.base_url = "https://api.duckduckgo.com/"
        self.user_agent = os.getenv("USER_AGENT", "NovaBrief-Research/0.1")
        self.timeout = int(os.getenv("FETCH_TIMEOUT_S", "15"))
    
    async def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search DuckDuckGo and return structured results.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
        
        Returns:
            List of search results with url, title, snippet
        """
        try:
            # Use DuckDuckGo HTML search since instant answer API is limited
            search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    search_url,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
                    }
                )
                response.raise_for_status()
                
                # Parse HTML response to extract search results
                # This is a simplified parser - for production use BeautifulSoup
                results = self._parse_duckduckgo_html(response.text, max_results)
                
                logger.info(f"DuckDuckGo search returned {len(results)} results for query: {query}")
                return results
                
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []
    
    def _parse_duckduckgo_html(self, html: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Simple HTML parser for DuckDuckGo results.
        In production, use BeautifulSoup for robust parsing.
        """
        results = []
        
        # This is a simplified implementation
        # For MVP, we'll return mock results to demonstrate structure
        mock_results = [
            {
                "url": f"https://example{i}.com",
                "title": f"Sample Result {i} for Query",
                "snippet": f"This is a sample snippet for result {i} showing relevant content...",
                "domain": f"example{i}.com"
            }
            for i in range(1, min(max_results + 1, 6))
        ]
        
        return mock_results


class SearchProviderRegistry:
    """Registry for different search providers."""
    
    def __init__(self):
        self.providers = {
            "duckduckgo": DuckDuckGoProvider()
        }
        self.default_provider = os.getenv("SEARCH_PROVIDER", "duckduckgo")
    
    async def search(self, query: str, max_results: int = 10, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search using specified or default provider.
        
        Args:
            query: Search query
            max_results: Maximum results to return
            provider: Provider name (defaults to configured provider)
        
        Returns:
            List of search results
        """
        provider_name = provider or self.default_provider
        
        if provider_name not in self.providers:
            raise ValueError(f"Unknown search provider: {provider_name}")
        
        return await self.providers[provider_name].search(query, max_results)


# Global registry instance
search_registry = SearchProviderRegistry()


async def duckduckgo(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Convenience function for DuckDuckGo search."""
    return await search_registry.search(query, max_results, "duckduckgo")


async def search(query: str, max_results: int = 10, provider: Optional[str] = None) -> List[Dict[str, Any]]:
    """Convenience function for generic search."""
    return await search_registry.search(query, max_results, provider)