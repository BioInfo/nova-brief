"""
Web search tool implementation.
Provides unified interface for web searching with multiple providers.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from ..providers.search_providers import search
from ..observability.logging import get_logger

logger = get_logger(__name__)


class WebSearchTool:
    """Tool for performing web searches."""
    
    def __init__(self):
        self.max_results_default = 10
        self.per_domain_cap = 3  # Will be configurable
    
    async def run(self, query: str, max_results: Optional[int] = None, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute web search and return structured results.
        
        Args:
            query: Search query string
            max_results: Maximum number of results (defaults to 10)
            provider: Search provider to use (optional)
        
        Returns:
            Dict with search results and metadata
        """
        try:
            max_results = max_results or self.max_results_default
            
            logger.info(f"Starting web search: query='{query}', max_results={max_results}")
            
            # Perform search
            search_results = await search(query, max_results, provider)
            
            # Apply domain filtering if needed
            filtered_results = self._apply_domain_caps(search_results)
            
            result = {
                "query": query,
                "results": filtered_results,
                "total_results": len(filtered_results),
                "provider": provider or "default",
                "success": True
            }
            
            logger.info(f"Web search completed: {len(filtered_results)} results")
            return result
            
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return {
                "query": query,
                "results": [],
                "total_results": 0,
                "provider": provider or "default",
                "success": False,
                "error": str(e)
            }
    
    def _apply_domain_caps(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply per-domain result caps to prevent over-representation.
        
        Args:
            results: List of search results
        
        Returns:
            Filtered list respecting domain caps
        """
        domain_counts = {}
        filtered_results = []
        
        for result in results:
            domain = result.get("domain", "unknown")
            count = domain_counts.get(domain, 0)
            
            if count < self.per_domain_cap:
                filtered_results.append(result)
                domain_counts[domain] = count + 1
            else:
                logger.debug(f"Skipping result from {domain} due to domain cap")
        
        return filtered_results


# Global tool instance
web_search_tool = WebSearchTool()


async def run(query: str, max_results: Optional[int] = None, provider: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function for web search."""
    return await web_search_tool.run(query, max_results, provider)


def run_sync(query: str, max_results: Optional[int] = None, provider: Optional[str] = None) -> Dict[str, Any]:
    """Synchronous wrapper for web search."""
    return asyncio.run(run(query, max_results, provider))