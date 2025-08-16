"""
Searcher agent module for executing web searches and collecting results.
Coordinates with search tools and manages result aggregation.
"""

import asyncio
from typing import List, Dict, Any, Optional
from ..tools.web_search import run as web_search_run
from ..observability.logging import get_logger
from ..observability.tracing import start_span, end_span

logger = get_logger(__name__)


class Searcher:
    """Search execution agent that runs queries and aggregates results."""
    
    def __init__(self):
        self.max_results_per_query = 10
        self.concurrent_searches = 3
        self.deduplication_threshold = 0.8  # For future similarity checking
    
    async def search(self, queries: List[str], max_results: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute multiple search queries and aggregate results.
        
        Args:
            queries: List of search queries to execute
            max_results: Maximum results per query (optional)
        
        Returns:
            Dict containing aggregated search results
        """
        span_id = start_span("search", "agent", {
            "query_count": len(queries),
            "max_results": max_results
        })
        
        try:
            logger.info(f"Executing {len(queries)} search queries")
            
            max_results = max_results or self.max_results_per_query
            
            # Execute searches concurrently in batches
            all_results = []
            all_search_metadata = []
            
            # Process queries in batches to avoid overwhelming providers
            for i in range(0, len(queries), self.concurrent_searches):
                batch = queries[i:i + self.concurrent_searches]
                batch_results = await self._execute_search_batch(batch, max_results)
                
                for query_result in batch_results:
                    if query_result["success"]:
                        all_results.extend(query_result["results"])
                    all_search_metadata.append({
                        "query": query_result["query"],
                        "result_count": query_result["total_results"],
                        "success": query_result["success"],
                        "error": query_result.get("error")
                    })
            
            # Deduplicate results
            deduplicated_results = self._deduplicate_results(all_results)
            
            # Calculate metrics
            total_queries = len(queries)
            successful_queries = sum(1 for meta in all_search_metadata if meta["success"])
            total_unique_results = len(deduplicated_results)
            
            result = {
                "queries": queries,
                "search_metadata": all_search_metadata,
                "results": deduplicated_results,
                "metrics": {
                    "total_queries": total_queries,
                    "successful_queries": successful_queries,
                    "total_raw_results": len(all_results),
                    "total_unique_results": total_unique_results,
                    "deduplication_ratio": 1 - (total_unique_results / max(len(all_results), 1))
                },
                "success": successful_queries > 0
            }
            
            logger.info(f"Search completed: {successful_queries}/{total_queries} queries successful, {total_unique_results} unique results")
            end_span(span_id, success=True, additional_data={
                "successful_queries": successful_queries,
                "total_results": total_unique_results
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Search execution failed: {e}"
            logger.error(error_msg)
            end_span(span_id, success=False, error=error_msg)
            return {
                "queries": queries,
                "search_metadata": [],
                "results": [],
                "metrics": {
                    "total_queries": len(queries),
                    "successful_queries": 0,
                    "total_raw_results": 0,
                    "total_unique_results": 0,
                    "deduplication_ratio": 0
                },
                "success": False,
                "error": str(e)
            }
    
    async def _execute_search_batch(self, queries: List[str], max_results: int) -> List[Dict[str, Any]]:
        """
        Execute a batch of search queries concurrently.
        
        Args:
            queries: Batch of queries to execute
            max_results: Maximum results per query
        
        Returns:
            List of search results for each query
        """
        tasks = []
        for query in queries:
            task = web_search_run(query, max_results)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions and convert to consistent format
        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Convert exception to error result
                formatted_results.append({
                    "query": queries[i],
                    "results": [],
                    "total_results": 0,
                    "success": False,
                    "error": str(result)
                })
            else:
                formatted_results.append(result)
        
        return formatted_results
    
    def _deduplicate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate results based on URL.
        
        Args:
            results: List of search results
        
        Returns:
            Deduplicated list of results
        """
        seen_urls = set()
        deduplicated = []
        
        for result in results:
            url = result.get("url", "")
            # Normalize URL for comparison
            normalized_url = self._normalize_url(url)
            
            if normalized_url not in seen_urls:
                seen_urls.add(normalized_url)
                # Add normalized URL for future reference
                result["normalized_url"] = normalized_url
                deduplicated.append(result)
            else:
                logger.debug(f"Skipping duplicate URL: {url}")
        
        return deduplicated
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL for deduplication.
        
        Args:
            url: Original URL
        
        Returns:
            Normalized URL
        """
        # Simple normalization - remove trailing slashes, fragments, some query params
        import urllib.parse
        
        try:
            parsed = urllib.parse.urlparse(url)
            
            # Remove common tracking parameters
            query_params = urllib.parse.parse_qs(parsed.query)
            filtered_params = {
                k: v for k, v in query_params.items()
                if k not in ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term']
            }
            
            # Rebuild query string
            filtered_query = urllib.parse.urlencode(filtered_params, doseq=True)
            
            # Normalize path (remove trailing slash)
            normalized_path = parsed.path.rstrip('/')
            if not normalized_path:
                normalized_path = '/'
            
            # Rebuild URL without fragment
            normalized = urllib.parse.urlunparse((
                parsed.scheme,
                parsed.netloc.lower(),
                normalized_path,
                parsed.params,
                filtered_query,
                ''  # Remove fragment
            ))
            
            return normalized
            
        except Exception:
            # If normalization fails, return original URL
            return url


# Global searcher instance
searcher = Searcher()


async def search(queries: List[str], max_results: Optional[int] = None) -> Dict[str, Any]:
    """Convenience function for search execution."""
    return await searcher.search(queries, max_results)