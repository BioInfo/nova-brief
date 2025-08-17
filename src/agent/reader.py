"""Reader component for fetching URLs and processing content into documents and chunks."""

import asyncio
from typing import Dict, List, Any, Optional
from ..tools.fetch_url import run as fetch_url_run
from ..tools.parse_pdf import run as parse_pdf_run
from ..tools.content_quality import validate_content, get_content_summary
from ..storage.models import SearchResult, Document, Chunk, Constraints, ResearchState, create_chunks_from_document
from ..observability.logging import get_logger
from ..observability.tracing import TimedOperation, emit_event

logger = get_logger(__name__)


async def read(
    search_results: List[SearchResult],
    constraints: Constraints,
    state: Optional[ResearchState] = None
) -> Dict[str, Any]:
    """
    Fetch URLs and process content into documents and chunks.
    
    Args:
        search_results: List of search results to fetch and process
        constraints: Research constraints including timeouts
        state: Research state to update with partial failures
    
    Returns:
        Dictionary with success status, documents, chunks, metadata, and partial_failures
    """
    with TimedOperation("agent_reader") as timer:
        try:
            if not search_results:
                return {
                    "success": False,
                    "error": "No search results provided",
                    "documents": [],
                    "chunks": []
                }
            
            urls = [result["url"] for result in search_results]
            logger.info(f"Reading {len(urls)} URLs")
            
            # Extract configuration
            fetch_timeout = constraints.get("fetch_timeout_s", 15.0)
            max_tokens_per_chunk = constraints.get("max_tokens_per_chunk", 1000)
            
            # Fetch URLs concurrently with controlled concurrency
            documents = []
            chunks = []
            fetch_results = await _fetch_urls_concurrent(urls, fetch_timeout)
            
            # Process each fetch result
            successful_fetches = 0
            failed_fetches = 0
            quality_gate_failures = 0
            partial_failures = []
            
            for i, fetch_result in enumerate(fetch_results):
                try:
                    search_result = search_results[i]
                    url = urls[i]
                    
                    if not fetch_result["success"]:
                        error_msg = fetch_result.get('error', 'Unknown fetch error')
                        logger.warning(f"Failed to fetch {url}: {error_msg}")
                        failed_fetches += 1
                        # Record as partial failure
                        partial_failures.append({
                            "source": url,
                            "error": f"Fetch failed: {error_msg}"
                        })
                        continue
                    
                    # Create document from fetch result (includes quality gate)
                    document_result = _create_document_from_fetch_result_with_quality_gate(
                        fetch_result, search_result
                    )
                    
                    if not document_result["success"]:
                        failed_fetches += 1
                        # Record quality gate or other failures
                        partial_failures.append({
                            "source": url,
                            "error": document_result["error"]
                        })
                        if "quality gate" in document_result["error"].lower():
                            quality_gate_failures += 1
                        continue
                    
                    document = document_result["document"]
                    documents.append(document)
                    successful_fetches += 1
                    
                    # Create chunks from document
                    doc_chunks = create_chunks_from_document(document, max_tokens_per_chunk)
                    chunks.extend(doc_chunks)
                    
                    logger.debug(f"Processed {url}: {len(doc_chunks)} chunks")
                    
                except Exception as e:
                    logger.error(f"Error processing result for {urls[i]}: {e}")
                    failed_fetches += 1
                    partial_failures.append({
                        "source": urls[i],
                        "error": f"Processing error: {str(e)}"
                    })
                    continue
            
            # Calculate metrics
            total_text_length = sum(len(doc["text"]) for doc in documents)
            total_chunks = len(chunks)
            avg_chunk_size = total_text_length / total_chunks if total_chunks > 0 else 0
            
            # Extract domain diversity
            domains = set()
            for doc in documents:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(doc["url"]).netloc
                    domains.add(domain)
                except Exception:
                    continue
            
            metadata = {
                "urls_requested": len(urls),
                "successful_fetches": successful_fetches,
                "failed_fetches": failed_fetches,
                "quality_gate_failures": quality_gate_failures,
                "documents_created": len(documents),
                "chunks_created": total_chunks,
                "total_text_length": total_text_length,
                "avg_chunk_size": int(avg_chunk_size),
                "domain_diversity": len(domains),
                "fetch_timeout": fetch_timeout,
                "partial_failures_count": len(partial_failures)
            }
            
            # Update state with partial failures if provided
            if state and partial_failures:
                state["partial_failures"].extend(partial_failures)
            
            logger.info(
                f"Reading completed: {successful_fetches}/{len(urls)} URLs, "
                f"{len(documents)} documents, {total_chunks} chunks, "
                f"{quality_gate_failures} quality gate failures",
                extra=metadata
            )
            
            emit_event(
                "reading_completed",
                metadata=metadata
            )
            
            return {
                "success": True,
                "documents": documents,
                "chunks": chunks,
                "metadata": metadata,
                "partial_failures": partial_failures
            }
            
        except Exception as e:
            logger.error(f"Reading operation failed: {e}")
            emit_event(
                "reading_error",
                metadata={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "urls_count": len(search_results) if search_results else 0
                }
            )
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "documents": [],
                "chunks": []
            }


async def _fetch_urls_concurrent(urls: List[str], timeout: float, max_concurrent: int = 5) -> List[Dict[str, Any]]:
    """Fetch URLs concurrently with controlled concurrency."""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def fetch_with_semaphore(url: str) -> Dict[str, Any]:
        async with semaphore:
            return await fetch_url_run(url, timeout=timeout)
    
    # Execute all fetches concurrently
    tasks = [fetch_with_semaphore(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Convert exceptions to error results
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append({
                "success": False,
                "error": str(result),
                "error_type": type(result).__name__,
                "url": urls[i]
            })
        else:
            processed_results.append(result)
    
    return processed_results


def _create_document_from_fetch_result_with_quality_gate(
    fetch_result: Dict[str, Any],
    search_result: SearchResult
) -> Dict[str, Any]:
    """Create a Document from fetch result and search result with quality gate validation."""
    try:
        url = fetch_result["url"]
        content_type = fetch_result.get("content_type", "text/html")
        
        # Handle PDF content
        if content_type == "application/pdf":
            # PDF parsing was already handled in fetch_url, but if raw content returned
            raw_content = fetch_result.get("raw_content")
            if raw_content and not fetch_result.get("text"):
                # Parse PDF content
                import asyncio
                pdf_result = asyncio.run(parse_pdf_run(raw_content))
                if pdf_result["success"]:
                    text = pdf_result["text"]
                    title = pdf_result.get("metadata", {}).get("title", "") or search_result["title"]
                else:
                    logger.warning(f"Failed to parse PDF content from {url}")
                    return {
                        "success": False,
                        "error": "Failed to parse PDF content",
                        "document": None
                    }
            else:
                text = fetch_result.get("text", "")
                title = fetch_result.get("title", "") or search_result["title"]
        else:
            # HTML or text content
            text = fetch_result.get("text", "")
            title = fetch_result.get("title", "") or search_result["title"]
        
        # Apply Content Quality Gate (Stage 1.5)
        quality_validation = validate_content(text)
        if not quality_validation["ok"]:
            reason = quality_validation["reason"]
            metrics_summary = get_content_summary(text)
            logger.warning(f"Content Quality Gate failed for {url}: {reason} ({metrics_summary})")
            return {
                "success": False,
                "error": f"Quality gate failed: {reason}",
                "document": None
            }
        
        # Extract domain for metadata
        try:
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            path = parsed_url.path
        except Exception:
            domain = "unknown"
            path = ""
        
        # Create document
        document: Document = {
            "url": url,
            "title": title.strip() if title else "",
            "text": text.strip(),
            "content_type": content_type,
            "source_meta": {
                "domain": domain,
                "path": path,
                "snippet": search_result["snippet"],
                "content_length": len(text),
                "fetch_metadata": fetch_result.get("metadata", {}),
                "quality_metrics": quality_validation["metrics"]
            }
        }
        
        return {
            "success": True,
            "document": document,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Error creating document from fetch result: {e}")
        return {
            "success": False,
            "error": f"Document creation error: {str(e)}",
            "document": None
        }


def _detect_content_language(text: str) -> str:
    """Simple language detection based on common words."""
    if not text:
        return "unknown"
    
    # Very basic detection - count common English words
    english_words = {
        "the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
        "a", "an", "is", "are", "was", "were", "be", "been", "have", "has", "had"
    }
    
    words = text.lower().split()[:100]  # Check first 100 words
    if not words:
        return "unknown"
    
    english_count = sum(1 for word in words if word in english_words)
    english_ratio = english_count / len(words)
    
    return "en" if english_ratio > 0.3 else "unknown"


def _extract_basic_metadata(text: str, url: str) -> Dict[str, Any]:
    """Extract basic metadata from text content."""
    metadata = {
        "char_count": len(text),
        "word_count": len(text.split()),
        "paragraph_count": len([p for p in text.split('\n\n') if p.strip()]),
        "language": _detect_content_language(text)
    }
    
    # Check for academic/research indicators
    academic_indicators = [
        "abstract", "introduction", "methodology", "results", "conclusion",
        "references", "doi:", "arxiv:", "journal", "university", "research"
    ]
    
    text_lower = text.lower()
    academic_score = sum(1 for indicator in academic_indicators if indicator in text_lower)
    metadata["academic_score"] = academic_score
    metadata["likely_academic"] = academic_score >= 3
    
    return metadata


# Utility functions for content processing
def filter_documents_by_quality(documents: List[Document], min_length: int = 500) -> List[Document]:
    """Filter documents by content quality."""
    filtered = []
    
    for doc in documents:
        text = doc["text"]
        
        # Minimum length check
        if len(text) < min_length:
            continue
        
        # Basic quality checks
        if _passes_content_quality_check(text):
            filtered.append(doc)
    
    return filtered


def _passes_content_quality_check(text: str) -> bool:
    """Check if content passes basic quality filters."""
    if not text or len(text.strip()) < 50:
        return False
    
    # Check for reasonable sentence structure
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    if len(sentences) < 3:
        return False
    
    # Check for excessive repetition (spam indicator)
    words = text.lower().split()
    if len(set(words)) < len(words) * 0.3:  # Less than 30% unique words
        return False
    
    return True


def group_chunks_by_document(chunks: List[Chunk]) -> Dict[str, List[Chunk]]:
    """Group chunks by their source document URL."""
    grouped = {}
    
    for chunk in chunks:
        doc_url = chunk["doc_url"]
        if doc_url not in grouped:
            grouped[doc_url] = []
        grouped[doc_url].append(chunk)
    
    return grouped