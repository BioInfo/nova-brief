"""Search providers for Nova Brief."""

import re
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse
import tldextract
from tenacity import retry, stop_after_attempt, wait_exponential

from ..observability.logging import get_logger
from ..observability.tracing import TimedOperation, emit_event

logger = get_logger(__name__)


class SearchResult:
    """Represents a search result with title, URL, and snippet."""
    
    def __init__(self, title: str, url: str, snippet: str):
        self.title = title.strip()
        self.url = self._normalize_url(url)
        self.snippet = snippet.strip()
    
    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize URL for deduplication."""
        # Ensure scheme is present
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Remove www. prefix and trailing slash for normalization
        normalized = re.sub(r'^https?://(www\.)?', 'https://', url)
        normalized = normalized.rstrip('/')
        
        return normalized
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary representation."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet
        }
    
    def __eq__(self, other) -> bool:
        return isinstance(other, SearchResult) and self.url == other.url
    
    def __hash__(self) -> int:
        return hash(self.url)


class DuckDuckGoProvider:
    """DuckDuckGo search provider."""
    
    def __init__(self):
        self.name = "duckduckgo"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    async def search(
        self,
        query: str,
        max_results: int = 10,
        region: str = "us-en"
    ) -> List[SearchResult]:
        """
        Search using DuckDuckGo.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            region: Search region (default: us-en)
        
        Returns:
            List of SearchResult objects
        """
        with TimedOperation(f"duckduckgo_search") as timer:
            try:
                # Import here to handle missing dependency gracefully
                from duckduckgo_search import DDGS
                
                logger.info(
                    f"Searching DuckDuckGo: {query}",
                    extra={"query": query, "max_results": max_results}
                )
                
                results = []
                with DDGS() as ddgs:
                    search_results = ddgs.text(
                        keywords=query,
                        region=region,
                        max_results=max_results,
                        backend="api"
                    )
                    
                    for result in search_results:
                        try:
                            search_result = SearchResult(
                                title=result.get("title", ""),
                                url=result.get("href", ""),
                                snippet=result.get("body", "")
                            )
                            results.append(search_result)
                        except Exception as e:
                            logger.warning(f"Failed to parse search result: {e}")
                            continue
                
                logger.info(
                    f"DuckDuckGo search completed: {len(results)} results",
                    extra={"query": query, "results_count": len(results)}
                )
                
                emit_event(
                    "search_completed",
                    metadata={
                        "provider": self.name,
                        "query": query,
                        "results_count": len(results)
                    }
                )
                
                return results
                
            except ImportError:
                logger.error("duckduckgo-search package not installed")
                raise ValueError("DuckDuckGo search provider not available")
            except Exception as e:
                logger.error(f"DuckDuckGo search failed: {e}")
                emit_event(
                    "search_error",
                    metadata={
                        "provider": self.name,
                        "query": query,
                        "error": str(e)
                    }
                )
                raise


class SearchManager:
    """Manages search operations with filtering and deduplication."""
    
    def __init__(self):
        self.providers = {
            "duckduckgo": DuckDuckGoProvider()
        }
    
    async def search(
        self,
        queries: List[str],
        provider: str = "duckduckgo",
        max_results_per_query: int = 10,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        per_domain_cap: int = 3
    ) -> List[SearchResult]:
        """
        Execute search queries with filtering and deduplication.
        
        Args:
            queries: List of search queries
            provider: Search provider name
            max_results_per_query: Maximum results per individual query
            include_domains: Domains to include (allowlist)
            exclude_domains: Domains to exclude (denylist)
            per_domain_cap: Maximum results per domain across all queries
        
        Returns:
            Deduplicated and filtered list of SearchResult objects
        """
        if provider not in self.providers:
            raise ValueError(f"Unknown search provider: {provider}")
        
        search_provider = self.providers[provider]
        all_results: List[SearchResult] = []
        
        for query in queries:
            try:
                results = await search_provider.search(query, max_results_per_query)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Search failed for query '{query}': {e}")
                continue
        
        # Deduplicate by URL
        unique_results = list({result.url: result for result in all_results}.values())
        
        # Apply domain filtering
        filtered_results = self._apply_domain_filters(
            unique_results,
            include_domains,
            exclude_domains
        )
        
        # Apply per-domain cap
        capped_results = self._apply_domain_cap(filtered_results, per_domain_cap)
        
        logger.info(
            f"Search completed: {len(all_results)} → {len(unique_results)} → "
            f"{len(filtered_results)} → {len(capped_results)} results",
            extra={
                "total_queries": len(queries),
                "raw_results": len(all_results),
                "deduplicated": len(unique_results),
                "filtered": len(filtered_results),
                "final": len(capped_results)
            }
        )
        
        return capped_results
    
    def _apply_domain_filters(
        self,
        results: List[SearchResult],
        include_domains: Optional[List[str]],
        exclude_domains: Optional[List[str]]
    ) -> List[SearchResult]:
        """Apply domain include/exclude filters."""
        if not include_domains and not exclude_domains:
            return results
        
        filtered = []
        include_set = set(include_domains or [])
        exclude_set = set(exclude_domains or [])
        
        for result in results:
            domain = self._extract_domain(result.url)
            
            # Skip if in exclude list
            if exclude_set and domain in exclude_set:
                continue
            
            # Include if no include list, or if in include list
            if not include_set or domain in include_set:
                filtered.append(result)
        
        return filtered
    
    def _apply_domain_cap(
        self,
        results: List[SearchResult],
        per_domain_cap: int
    ) -> List[SearchResult]:
        """Apply per-domain result cap."""
        domain_counts: Dict[str, int] = {}
        capped_results = []
        
        for result in results:
            domain = self._extract_domain(result.url)
            current_count = domain_counts.get(domain, 0)
            
            if current_count < per_domain_cap:
                capped_results.append(result)
                domain_counts[domain] = current_count + 1
        
        return capped_results
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL."""
        try:
            extracted = tldextract.extract(url)
            return f"{extracted.domain}.{extracted.suffix}"
        except Exception:
            return urlparse(url).netloc


# Convenience function for backward compatibility
async def duckduckgo(
    query: str,
    max_results: int = 10
) -> List[Dict[str, str]]:
    """
    Convenience function for DuckDuckGo search.
    
    Args:
        query: Search query
        max_results: Maximum results to return
    
    Returns:
        List of result dictionaries
    """
    provider = DuckDuckGoProvider()
    results = await provider.search(query, max_results)
    return [result.to_dict() for result in results]