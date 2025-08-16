"""Verifier component for citation validation and coverage enforcement."""

import asyncio
from typing import Dict, List, Any, Set, Optional
from urllib.parse import urlparse
import httpx
from ..storage.models import Claim, Citation, Document, Constraints
from ..observability.logging import get_logger
from ..observability.tracing import TimedOperation, emit_event

logger = get_logger(__name__)


async def verify(
    claims: List[Claim],
    citations: List[Citation],
    documents: List[Document],
    constraints: Constraints,
    target_sources_per_claim: int = 1
) -> Dict[str, Any]:
    """
    Verify claim coverage and citation quality.
    
    Args:
        claims: List of claims to verify
        citations: List of citations linking claims to sources
        documents: List of available documents
        constraints: Research constraints
        target_sources_per_claim: Minimum sources required per claim
    
    Returns:
        Dictionary with verification results and follow-up recommendations
    """
    with TimedOperation("agent_verifier") as timer:
        try:
            if not claims:
                return {
                    "success": True,
                    "unsupported_claims": [],
                    "follow_up_queries": [],
                    "updated_citations": citations,
                    "coverage_report": {
                        "total_claims": 0,
                        "supported_claims": 0,
                        "coverage_percentage": 100.0
                    }
                }
            
            logger.info(f"Verifying {len(claims)} claims with {len(citations)} citations")
            
            # Create mappings for efficient lookup
            citation_map = {cit["claim_id"]: cit for cit in citations}
            available_urls = {doc["url"] for doc in documents}
            
            # Verify each claim
            verification_results = []
            
            for claim in claims:
                result = await _verify_single_claim(
                    claim, 
                    citation_map.get(claim["id"]), 
                    available_urls,
                    target_sources_per_claim
                )
                verification_results.append(result)
            
            # Identify unsupported claims
            unsupported_claims = [
                result["claim"] for result in verification_results 
                if not result["is_supported"]
            ]
            
            # Check URL accessibility for citations
            url_check_results = await _check_citation_urls(citations, documents)
            
            # Update citations based on URL checks
            updated_citations = _update_citations_with_url_checks(
                citations, 
                url_check_results
            )
            
            # Generate follow-up queries for unsupported claims
            follow_up_queries = _generate_follow_up_queries(
                unsupported_claims, 
                verification_results
            )
            
            # Calculate coverage metrics
            supported_count = len([r for r in verification_results if r["is_supported"]])
            coverage_percentage = (supported_count / len(claims)) * 100 if claims else 100.0
            
            # Analyze domain diversity
            domain_diversity = _analyze_domain_diversity(updated_citations, documents)
            
            coverage_report = {
                "total_claims": len(claims),
                "supported_claims": supported_count,
                "unsupported_claims": len(unsupported_claims),
                "coverage_percentage": round(coverage_percentage, 1),
                "target_sources_per_claim": target_sources_per_claim,
                "domain_diversity": domain_diversity,
                "accessible_citations": sum(1 for r in url_check_results.values() if r["accessible"]),
                "total_citation_urls": len(url_check_results)
            }
            
            # Determine if additional research is needed
            needs_follow_up = (
                coverage_percentage < 80.0 or 
                len(unsupported_claims) > len(claims) * 0.3 or
                domain_diversity["unique_domains"] < 3
            )
            
            logger.info(
                f"Verification completed: {coverage_percentage:.1f}% coverage, "
                f"{len(unsupported_claims)} unsupported claims",
                extra=coverage_report
            )
            
            emit_event(
                "verification_completed",
                metadata={
                    **coverage_report,
                    "needs_follow_up": needs_follow_up,
                    "follow_up_queries_count": len(follow_up_queries)
                }
            )
            
            return {
                "success": True,
                "unsupported_claims": unsupported_claims,
                "follow_up_queries": follow_up_queries,
                "updated_citations": updated_citations,
                "coverage_report": coverage_report,
                "verification_details": verification_results,
                "url_check_results": url_check_results,
                "needs_follow_up": needs_follow_up
            }
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            emit_event(
                "verification_error",
                metadata={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "claims_count": len(claims) if claims else 0
                }
            )
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "unsupported_claims": [],
                "follow_up_queries": [],
                "updated_citations": citations,
                "coverage_report": {
                    "total_claims": len(claims) if claims else 0,
                    "supported_claims": 0,
                    "coverage_percentage": 0.0
                }
            }


async def _verify_single_claim(
    claim: Claim,
    citation: Citation,
    available_urls: Set[str],
    target_sources: int
) -> Dict[str, Any]:
    """Verify a single claim's citation support."""
    
    # Check if claim needs citation (non-obvious claims)
    needs_citation = _claim_needs_citation(claim)
    
    if not needs_citation:
        return {
            "claim": claim,
            "is_supported": True,
            "support_level": "obvious",
            "available_sources": 0,
            "issues": []
        }
    
    # Check citation exists
    if not citation:
        return {
            "claim": claim,
            "is_supported": False,
            "support_level": "none",
            "available_sources": 0,
            "issues": ["No citation provided"]
        }
    
    # Check citation URLs are available
    citation_urls = citation["urls"]
    available_citation_urls = [url for url in citation_urls if url in available_urls]
    
    issues = []
    
    if not available_citation_urls:
        issues.append("No cited sources available in document set")
    elif len(available_citation_urls) < target_sources:
        issues.append(f"Only {len(available_citation_urls)} source(s), target is {target_sources}")
    
    # Check for domain diversity
    if len(available_citation_urls) > 1:
        domains = set()
        for url in available_citation_urls:
            try:
                domain = urlparse(url).netloc
                domains.add(domain)
            except Exception:
                continue
        
        if len(domains) < len(available_citation_urls):
            issues.append("Multiple sources from same domain - limited diversity")
    
    # Determine support level
    source_count = len(available_citation_urls)
    if source_count >= target_sources:
        support_level = "strong" if source_count >= 2 else "adequate"
        is_supported = True
    else:
        support_level = "weak"
        is_supported = source_count > 0
    
    return {
        "claim": claim,
        "is_supported": is_supported,
        "support_level": support_level,
        "available_sources": source_count,
        "cited_urls": available_citation_urls,
        "issues": issues
    }


def _claim_needs_citation(claim: Claim) -> bool:
    """Determine if a claim needs citation support."""
    claim_text = claim["text"].lower()
    
    # Obvious/common knowledge patterns that don't need citation
    obvious_patterns = [
        "is a", "are known as", "commonly", "generally", 
        "typically", "usually", "widely", "broadly"
    ]
    
    # Claims that definitely need citation
    needs_citation_patterns = [
        "research shows", "study found", "according to", "data indicates",
        "statistics show", "report states", "analysis reveals", "survey",
        "%", "percent", "million", "billion", "increase", "decrease",
        "compared to", "versus", "growth", "decline"
    ]
    
    # Check if claim has specific numbers or research references
    has_specifics = any(pattern in claim_text for pattern in needs_citation_patterns)
    
    # Check if claim appears to be obvious
    appears_obvious = any(pattern in claim_text for pattern in obvious_patterns)
    
    # Opinion claims with high confidence need support
    if claim["type"] == "opinion" and claim["confidence"] > 0.7:
        return True
    
    # Fact and estimate claims generally need citation
    if claim["type"] in ["fact", "estimate"]:
        return not appears_obvious or has_specifics
    
    # Default: if it has specific data, it needs citation
    return has_specifics


async def _check_citation_urls(
    citations: List[Citation], 
    documents: List[Document],
    timeout: float = 5.0
) -> Dict[str, Dict[str, Any]]:
    """Check URL accessibility for citation validation."""
    
    # Collect all unique URLs from citations
    all_urls = set()
    for citation in citations:
        all_urls.update(citation["urls"])
    
    # Quick check: if URL is in our documents, consider it accessible
    document_urls = {doc["url"] for doc in documents}
    
    url_results = {}
    
    # Check each URL
    for url in all_urls:
        if url in document_urls:
            # We already have this document, so it's accessible
            url_results[url] = {
                "accessible": True,
                "status_code": 200,
                "method": "document_cache",
                "error": None
            }
        else:
            # Check URL accessibility with a quick HEAD request
            result = await _check_single_url(url, timeout)
            url_results[url] = result
    
    return url_results


async def _check_single_url(url: str, timeout: float) -> Dict[str, Any]:
    """Check if a single URL is accessible."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.head(url, follow_redirects=True)
            return {
                "accessible": response.status_code < 400,
                "status_code": response.status_code,
                "method": "http_head",
                "error": None
            }
    except httpx.TimeoutException:
        return {
            "accessible": False,
            "status_code": None,
            "method": "http_head",
            "error": "timeout"
        }
    except Exception as e:
        return {
            "accessible": False,
            "status_code": None,
            "method": "http_head",
            "error": str(e)
        }


def _update_citations_with_url_checks(
    citations: List[Citation],
    url_check_results: Dict[str, Dict[str, Any]]
) -> List[Citation]:
    """Update citations to remove inaccessible URLs."""
    updated_citations = []
    
    for citation in citations:
        accessible_urls = [
            url for url in citation["urls"]
            if url_check_results.get(url, {}).get("accessible", False)
        ]
        
        if accessible_urls:
            updated_citation = citation.copy()
            updated_citation["urls"] = accessible_urls
            updated_citations.append(updated_citation)
        else:
            # Keep citation but mark as problematic
            logger.warning(f"No accessible URLs for claim {citation['claim_id']}")
            updated_citations.append(citation)
    
    return updated_citations


def _generate_follow_up_queries(
    unsupported_claims: List[Claim],
    verification_results: List[Dict[str, Any]]
) -> List[str]:
    """Generate follow-up search queries for unsupported claims."""
    follow_up_queries = []
    
    # Group unsupported claims by type
    weak_claims = [
        result for result in verification_results
        if result["support_level"] in ["weak", "none"]
    ]
    
    for result in weak_claims[:5]:  # Limit to 5 follow-up queries
        claim = result["claim"]
        claim_text = claim["text"]
        
        # Generate specific queries based on claim content
        if claim["type"] == "fact":
            queries = [
                f'"{claim_text}" research evidence',
                f'{_extract_key_terms(claim_text)} scientific study',
                f'{_extract_key_terms(claim_text)} official report'
            ]
        elif claim["type"] == "estimate":
            queries = [
                f'{_extract_key_terms(claim_text)} statistics data',
                f'{_extract_key_terms(claim_text)} market research',
                f'{_extract_key_terms(claim_text)} analysis report'
            ]
        else:  # opinion
            queries = [
                f'{_extract_key_terms(claim_text)} expert opinion',
                f'{_extract_key_terms(claim_text)} industry analysis',
                f'{_extract_key_terms(claim_text)} professional view'
            ]
        
        # Add the best query
        if queries:
            follow_up_queries.append(queries[0])
    
    return follow_up_queries


def _extract_key_terms(text: str) -> str:
    """Extract key terms from claim text for search queries."""
    # Simple extraction of important words (skip common words)
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", 
        "of", "with", "by", "is", "are", "was", "were", "be", "been", "have", 
        "has", "had", "that", "this", "these", "those", "will", "would", "could"
    }
    
    words = text.lower().split()
    key_words = [word for word in words if word not in stop_words and len(word) > 3]
    
    return " ".join(key_words[:4])  # Return top 4 key terms


def _analyze_domain_diversity(
    citations: List[Citation], 
    documents: List[Document]
) -> Dict[str, Any]:
    """Analyze domain diversity in citations."""
    
    all_domains = set()
    domain_counts = {}
    
    for citation in citations:
        for url in citation["urls"]:
            try:
                domain = urlparse(url).netloc
                all_domains.add(domain)
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
            except Exception:
                continue
    
    # Calculate diversity metrics
    total_citations = sum(domain_counts.values())
    unique_domains = len(all_domains)
    
    # Find most cited domains
    top_domains = sorted(domain_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        "unique_domains": unique_domains,
        "total_citations": total_citations,
        "diversity_ratio": unique_domains / total_citations if total_citations > 0 else 0,
        "top_domains": top_domains,
        "domain_distribution": domain_counts
    }


# Utility functions for verification
def calculate_citation_strength(citation: Citation, available_urls: Set[str]) -> float:
    """Calculate citation strength score (0.0 to 1.0)."""
    if not citation["urls"]:
        return 0.0
    
    accessible_count = sum(1 for url in citation["urls"] if url in available_urls)
    availability_score = accessible_count / len(citation["urls"])
    
    # Bonus for multiple sources
    diversity_bonus = min(accessible_count / 2, 0.5)  # Up to 0.5 bonus for 2+ sources
    
    return min(availability_score + diversity_bonus, 1.0)


def group_claims_by_support_level(
    verification_results: List[Dict[str, Any]]
) -> Dict[str, List[Claim]]:
    """Group claims by their support level."""
    grouped = {
        "strong": [],
        "adequate": [],
        "weak": [],
        "none": [],
        "obvious": []
    }
    
    for result in verification_results:
        support_level = result["support_level"]
        claim = result["claim"]
        grouped[support_level].append(claim)
    
    return grouped