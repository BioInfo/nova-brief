"""Searcher component for executing web searches and collecting results."""

from typing import Dict, List, Any
from ..tools.web_search import run as web_search_run
from ..storage.models import SearchResult, Constraints
from ..observability.logging import get_logger
from ..observability.tracing import TimedOperation, emit_event

logger = get_logger(__name__)


async def search(
    queries: List[str],
    constraints: Constraints,
    provider: str = "duckduckgo",
    max_results_per_query: int = 10
) -> Dict[str, Any]:
    """
    Execute search queries using the configured search provider.
    
    Args:
        queries: List of search query strings
        constraints: Research constraints including domain filters
        provider: Search provider to use (default: duckduckgo)
        max_results_per_query: Maximum results per individual query
    
    Returns:
        Dictionary with success status, search results, and metadata
    """
    with TimedOperation("agent_searcher") as timer:
        try:
            if not queries:
                return {
                    "success": False,
                    "error": "No search queries provided",
                    "search_results": []
                }
            
            logger.info(
                f"Executing search: {len(queries)} queries with {provider}",
                extra={
                    "queries": queries,
                    "provider": provider,
                    "max_results_per_query": max_results_per_query,
                    "per_domain_cap": constraints.get("per_domain_cap", 3)
                }
            )
            
            # Extract domain constraints
            include_domains = constraints.get("include_domains", [])
            exclude_domains = constraints.get("exclude_domains", [])
            per_domain_cap = constraints.get("per_domain_cap", 3)
            
            # Execute web search
            search_result = await web_search_run(
                queries=queries,
                provider=provider,
                max_results_per_query=max_results_per_query,
                include_domains=include_domains if include_domains else None,
                exclude_domains=exclude_domains if exclude_domains else None,
                per_domain_cap=per_domain_cap
            )
            
            if not search_result["success"]:
                logger.error(f"Web search failed: {search_result.get('error')}")
                return {
                    "success": False,
                    "error": f"SEARCH_FAILED: {search_result.get('error')}",
                    "search_results": []
                }
            
            # Convert to SearchResult objects
            raw_results = search_result.get("results", [])
            search_results = []
            
            for result_dict in raw_results:
                try:
                    # Validate and normalize result
                    if not _validate_search_result(result_dict):
                        logger.warning(f"Invalid search result skipped: {result_dict}")
                        continue
                    
                    search_results.append({
                        "title": result_dict["title"].strip(),
                        "url": result_dict["url"].strip(),
                        "snippet": result_dict["snippet"].strip()
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing search result: {e}")
                    continue
            
            # Apply additional filtering and validation
            search_results = _post_process_results(search_results, constraints)
            
            # Calculate metrics
            domains = set()
            for result in search_results:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(result["url"]).netloc
                    domains.add(domain)
                except Exception:
                    continue
            
            metrics = {
                "total_queries": len(queries),
                "results_count": len(search_results),
                "domain_diversity": len(domains),
                "provider": provider,
                "per_domain_cap": per_domain_cap
            }
            
            logger.info(
                f"Search completed: {len(search_results)} results from {len(domains)} domains",
                extra=metrics
            )
            
            emit_event(
                "search_completed",
                metadata=metrics
            )
            
            return {
                "success": True,
                "search_results": search_results,
                "metadata": metrics
            }
            
        except Exception as e:
            logger.error(f"Search operation failed: {e}")
            emit_event(
                "search_error",
                metadata={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "queries_count": len(queries) if queries else 0
                }
            )
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "search_results": []
            }


def _validate_search_result(result: Dict[str, Any]) -> bool:
    """Validate a search result dictionary."""
    required_fields = {"title", "url", "snippet"}
    
    # Check required fields exist and are strings
    if not all(field in result and isinstance(result[field], str) for field in required_fields):
        return False
    
    # Check URL format
    url = result["url"]
    if not url.startswith(("http://", "https://")):
        return False
    
    # Check for minimum content
    if not result["title"].strip() or not result["url"].strip():
        return False
    
    return True


def _post_process_results(results: List[Dict[str, Any]], constraints: Constraints) -> List[Dict[str, Any]]:
    """Apply additional filtering and validation to search results."""
    processed_results = []
    seen_urls = set()
    
    for result in results:
        # Skip duplicates
        url = result["url"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        
        # Apply quality filters
        if _passes_quality_filters(result, constraints):
            processed_results.append(result)
    
    return processed_results


def _passes_quality_filters(result: Dict[str, Any], constraints: Constraints) -> bool:
    """Check if a search result passes quality filters."""
    
    # Minimum content length
    if len(result["title"]) < 10 or len(result["snippet"]) < 20:
        return False
    
    # Check for spam patterns
    title = result["title"].lower()
    snippet = result["snippet"].lower()
    
    # Simple spam detection
    spam_patterns = [
        "click here", "buy now", "free download", "limited time",
        "act now", "special offer", "$$$", "make money"
    ]
    
    text_to_check = f"{title} {snippet}"
    spam_score = sum(1 for pattern in spam_patterns if pattern in text_to_check)
    
    if spam_score >= 2:
        logger.debug(f"Filtered spam result: {result['title']}")
        return False
    
    # Check for reasonable title length (not too long, likely spam)
    if len(result["title"]) > 200:
        return False
    
    return True


# Utility functions for search result processing
def extract_domains_from_results(results: List[Dict[str, Any]]) -> List[str]:
    """Extract unique domains from search results."""
    domains = set()
    
    for result in results:
        try:
            from urllib.parse import urlparse
            domain = urlparse(result["url"]).netloc
            if domain:
                domains.add(domain)
        except Exception:
            continue
    
    return sorted(list(domains))


def filter_results_by_domain(
    results: List[Dict[str, Any]], 
    allowed_domains: List[str]
) -> List[Dict[str, Any]]:
    """Filter search results to only include specified domains."""
    if not allowed_domains:
        return results
    
    filtered_results = []
    allowed_set = set(allowed_domains)
    
    for result in results:
        try:
            from urllib.parse import urlparse
            domain = urlparse(result["url"]).netloc
            if domain in allowed_set:
                filtered_results.append(result)
        except Exception:
            continue
    
    return filtered_results


def group_results_by_domain(results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group search results by domain."""
    grouped = {}
    
    for result in results:
        try:
            from urllib.parse import urlparse
            domain = urlparse(result["url"]).netloc
            if domain not in grouped:
                grouped[domain] = []
            grouped[domain].append(result)
        except Exception:
            continue
    
    return grouped