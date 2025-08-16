"""Web search tool for Nova Brief."""

from typing import Dict, List, Optional, Any
from ..providers.search_providers import SearchManager
from ..observability.logging import get_logger

logger = get_logger(__name__)


async def run(
    queries: List[str],
    provider: str = "duckduckgo",
    max_results_per_query: int = 10,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    per_domain_cap: int = 3
) -> Dict[str, Any]:
    """
    Execute web search queries and return results.
    
    Args:
        queries: List of search query strings
        provider: Search provider to use (default: duckduckgo)
        max_results_per_query: Maximum results per query
        include_domains: Domains to include (allowlist)
        exclude_domains: Domains to exclude (denylist)
        per_domain_cap: Maximum results per domain
    
    Returns:
        Dictionary with success status, search results, and metadata
    """
    try:
        if not queries:
            return {
                "success": False,
                "error": "No search queries provided",
                "results": []
            }
        
        search_manager = SearchManager()
        
        logger.info(
            f"Executing web search: {len(queries)} queries",
            extra={
                "queries": queries,
                "provider": provider,
                "max_results_per_query": max_results_per_query,
                "per_domain_cap": per_domain_cap
            }
        )
        
        results = await search_manager.search(
            queries=queries,
            provider=provider,
            max_results_per_query=max_results_per_query,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            per_domain_cap=per_domain_cap
        )
        
        # Convert to dictionaries for serialization
        result_dicts = [result.to_dict() for result in results]
        
        logger.info(
            f"Web search completed: {len(result_dicts)} results",
            extra={
                "total_queries": len(queries),
                "results_count": len(result_dicts),
                "provider": provider
            }
        )
        
        return {
            "success": True,
            "results": result_dicts,
            "metadata": {
                "queries": queries,
                "provider": provider,
                "results_count": len(result_dicts),
                "per_domain_cap": per_domain_cap
            }
        }
        
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "results": []
        }