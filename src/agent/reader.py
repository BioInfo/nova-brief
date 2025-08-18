"""Reader component for fetching URLs and processing content into documents and chunks with structural extraction."""

import asyncio
import re
import json
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
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
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            path = parsed_url.path
        except Exception:
            domain = "unknown"
            path = ""
        
        # Enhanced structural content extraction
        structural_data = _extract_structural_content(text, url, content_type)
        content_classification = _classify_content(text, url, title)
        enhanced_metadata = _extract_enhanced_metadata(text, url, title)
        
        # Create document with enhanced structure
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
                "quality_metrics": quality_validation["metrics"],
                # Enhanced structural metadata
                "structure": structural_data,
                "classification": content_classification,
                "enhanced_metadata": enhanced_metadata
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


# Enhanced structural content extraction functions
def _extract_structural_content(text: str, url: str, content_type: str) -> Dict[str, Any]:
    """Extract structural elements from content including headings, sections, and key elements."""
    structure = {
        "headings": [],
        "sections": [],
        "key_sections": {},
        "lists": [],
        "tables": [],
        "citations": [],
        "outline": []
    }
    
    try:
        # Extract headings (markdown-style and numbered)
        structure["headings"] = _extract_headings(text)
        
        # Extract sections based on headings and content breaks
        structure["sections"] = _extract_sections(text, structure["headings"])
        
        # Identify key sections for different content types
        structure["key_sections"] = _identify_key_sections(text, url, content_type)
        
        # Extract lists and numbered items
        structure["lists"] = _extract_lists(text)
        
        # Extract table-like content
        structure["tables"] = _extract_tables(text)
        
        # Extract citations and references
        structure["citations"] = _extract_citations(text)
        
        # Generate content outline
        structure["outline"] = _generate_content_outline(text, structure["headings"])
        
    except Exception as e:
        logger.warning(f"Error extracting structural content from {url}: {e}")
        # Return basic structure on error
        structure = {
            "headings": [],
            "sections": [],
            "key_sections": {},
            "lists": [],
            "tables": [],
            "citations": [],
            "outline": [],
            "extraction_error": str(e)
        }
    
    return structure


def _extract_headings(text: str) -> List[Dict[str, Any]]:
    """Extract headings from text using various patterns."""
    headings = []
    lines = text.split('\n')
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        # Markdown-style headings
        if line.startswith('#'):
            level = len(line) - len(line.lstrip('#'))
            title = line.lstrip('#').strip()
            if title:
                headings.append({
                    "level": level,
                    "title": title,
                    "line_number": i + 1,
                    "type": "markdown"
                })
        
        # ALL CAPS headings (likely section headers)
        elif line.isupper() and len(line) > 5 and len(line.split()) >= 2:
            headings.append({
                "level": 2,  # Assume level 2 for caps headings
                "title": line,
                "line_number": i + 1,
                "type": "caps"
            })
        
        # Numbered headings (1. Introduction, 2.1 Methods, etc.)
        elif re.match(r'^\d+(\.\d+)*\.?\s+[A-Z]', line):
            match = re.match(r'^(\d+(?:\.\d+)*)\.?\s+(.+)', line)
            if match:
                number, title = match.groups()
                level = len(number.split('.'))
                headings.append({
                    "level": level,
                    "title": title.strip(),
                    "number": number,
                    "line_number": i + 1,
                    "type": "numbered"
                })
    
    return headings


def _extract_sections(text: str, headings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract sections based on headings and content breaks."""
    sections = []
    lines = text.split('\n')
    
    if not headings:
        # If no headings, try to identify sections by paragraph breaks
        paragraphs = text.split('\n\n')
        for i, para in enumerate(paragraphs):
            if len(para.strip()) > 100:  # Substantial content
                sections.append({
                    "title": f"Section {i + 1}",
                    "content": para.strip(),
                    "start_position": text.find(para),
                    "word_count": len(para.split()),
                    "type": "paragraph_based"
                })
        return sections
    
    # Extract sections based on headings
    for i, heading in enumerate(headings):
        start_line = heading["line_number"] - 1
        
        # Find end line (next heading or end of text)
        if i + 1 < len(headings):
            end_line = headings[i + 1]["line_number"] - 1
        else:
            end_line = len(lines)
        
        # Extract section content
        section_lines = lines[start_line + 1:end_line]
        content = '\n'.join(section_lines).strip()
        
        if content:  # Only add sections with content
            sections.append({
                "title": heading["title"],
                "content": content,
                "heading": heading,
                "start_line": start_line + 1,
                "end_line": end_line,
                "word_count": len(content.split()),
                "type": "heading_based"
            })
    
    return sections


def _identify_key_sections(text: str, url: str, content_type: str) -> Dict[str, Any]:
    """Identify key sections like abstract, introduction, conclusion, etc."""
    key_sections = {}
    text_lower = text.lower()
    
    # Academic paper sections
    academic_sections = {
        "abstract": [r"\babstract\b", r"\bsummary\b"],
        "introduction": [r"\bintroduction\b", r"\bintro\b", r"\bbackground\b"],
        "methodology": [r"\bmethodology\b", r"\bmethods\b", r"\bapproach\b"],
        "results": [r"\bresults\b", r"\bfindings\b"],
        "discussion": [r"\bdiscussion\b", r"\banalysis\b"],
        "conclusion": [r"\bconclusion\b", r"\bconcluding\b", r"\bconclusions\b"],
        "references": [r"\breferences\b", r"\bbibliography\b", r"\bcitations\b"]
    }
    
    # News article sections
    news_sections = {
        "headline": [r"\bheadline\b", r"\btitle\b"],
        "lead": [r"\blead\b", r"\bsummary\b"],
        "body": [r"\bbody\b", r"\bmain\b"],
        "quotes": [r'["""][^"""]*["""]', r"'[^']*'"]
    }
    
    # Blog post sections
    blog_sections = {
        "introduction": [r"\bintro\b", r"\bintroduction\b"],
        "main_content": [r"\bmain\b", r"\bcontent\b"],
        "conclusion": [r"\bconclusion\b", r"\bwrap.up\b", r"\bfinal\b"]
    }
    
    # Choose section patterns based on content type and URL
    if _is_academic_content(text, url):
        section_patterns = academic_sections
    elif _is_news_content(text, url):
        section_patterns = news_sections
    else:
        section_patterns = blog_sections
    
    # Find sections
    for section_name, patterns in section_patterns.items():
        for pattern in patterns:
            matches = list(re.finditer(pattern, text_lower))
            if matches:
                # Get the content around the match
                for match in matches:
                    start_pos = max(0, match.start() - 50)
                    end_pos = min(len(text), match.end() + 500)
                    context = text[start_pos:end_pos]
                    
                    key_sections[section_name] = {
                        "found": True,
                        "position": match.start(),
                        "context": context.strip(),
                        "pattern_matched": pattern
                    }
                    break  # Use first match
                break  # Use first successful pattern
    
    return key_sections


def _extract_lists(text: str) -> List[Dict[str, Any]]:
    """Extract bulleted and numbered lists from text."""
    lists = []
    lines = text.split('\n')
    current_list = None
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            if current_list:
                lists.append(current_list)
                current_list = None
            continue
        
        # Detect list items
        list_patterns = [
            (r'^[-*•]\s+(.+)', "bullet"),
            (r'^\d+\.\s+(.+)', "numbered"),
            (r'^[a-zA-Z]\.\s+(.+)', "lettered"),
            (r'^[ivx]+\.\s+(.+)', "roman")
        ]
        
        for pattern, list_type in list_patterns:
            match = re.match(pattern, line)
            if match:
                item_text = match.group(1)
                
                if not current_list or current_list["type"] != list_type:
                    if current_list:
                        lists.append(current_list)
                    current_list = {
                        "type": list_type,
                        "items": [],
                        "start_line": i + 1
                    }
                
                current_list["items"].append({
                    "text": item_text,
                    "line_number": i + 1
                })
                break
        else:
            # Not a list item
            if current_list:
                lists.append(current_list)
                current_list = None
    
    # Add final list if exists
    if current_list:
        lists.append(current_list)
    
    return lists


def _extract_tables(text: str) -> List[Dict[str, Any]]:
    """Extract table-like content from text."""
    tables = []
    lines = text.split('\n')
    
    # Look for pipe-separated tables (markdown style)
    table_lines = []
    for i, line in enumerate(lines):
        if '|' in line and line.count('|') >= 2:
            table_lines.append((i, line))
        else:
            if len(table_lines) >= 2:  # At least header + one row
                tables.append(_process_table_lines(table_lines))
            table_lines = []
    
    # Check final table
    if len(table_lines) >= 2:
        tables.append(_process_table_lines(table_lines))
    
    # Look for tab-separated content
    for i, line in enumerate(lines):
        if '\t' in line and line.count('\t') >= 2:
            # Check surrounding lines for similar structure
            tab_lines = [(i, line)]
            
            # Check previous and next lines
            for j in range(max(0, i-3), min(len(lines), i+4)):
                if j != i and '\t' in lines[j] and lines[j].count('\t') >= 2:
                    tab_lines.append((j, lines[j]))
            
            if len(tab_lines) >= 2:
                tables.append(_process_tab_separated_table(tab_lines))
    
    return tables


def _process_table_lines(table_lines: List[tuple]) -> Dict[str, Any]:
    """Process pipe-separated table lines."""
    rows = []
    for line_num, line in table_lines:
        # Skip separator lines (containing only |, -, :, spaces)
        if re.match(r'^[\s|:-]+$', line):
            continue
        
        cells = [cell.strip() for cell in line.split('|')]
        # Remove empty cells from start/end
        while cells and not cells[0]:
            cells.pop(0)
        while cells and not cells[-1]:
            cells.pop()
        
        if cells:
            rows.append({
                "cells": cells,
                "line_number": line_num + 1
            })
    
    return {
        "type": "pipe_separated",
        "rows": rows,
        "column_count": max(len(row["cells"]) for row in rows) if rows else 0,
        "row_count": len(rows)
    }


def _process_tab_separated_table(tab_lines: List[tuple]) -> Dict[str, Any]:
    """Process tab-separated table lines."""
    rows = []
    for line_num, line in tab_lines:
        cells = [cell.strip() for cell in line.split('\t')]
        if any(cell for cell in cells):  # At least one non-empty cell
            rows.append({
                "cells": cells,
                "line_number": line_num + 1
            })
    
    return {
        "type": "tab_separated",
        "rows": rows,
        "column_count": max(len(row["cells"]) for row in rows) if rows else 0,
        "row_count": len(rows)
    }


def _extract_citations(text: str) -> List[Dict[str, Any]]:
    """Extract citations and references from text."""
    citations = []
    
    # DOI patterns
    doi_pattern = r'\b(doi:|DOI:)\s*([^\s]+)'
    for match in re.finditer(doi_pattern, text, re.IGNORECASE):
        citations.append({
            "type": "doi",
            "value": match.group(2),
            "position": match.start(),
            "context": text[max(0, match.start()-50):match.end()+50]
        })
    
    # arXiv patterns
    arxiv_pattern = r'\b(arxiv:|arXiv:)\s*([^\s]+)'
    for match in re.finditer(arxiv_pattern, text, re.IGNORECASE):
        citations.append({
            "type": "arxiv",
            "value": match.group(2),
            "position": match.start(),
            "context": text[max(0, match.start()-50):match.end()+50]
        })
    
    # URL citations
    url_pattern = r'https?://[^\s<>"\'\)]+[^\s<>"\'\.\,\)\!]'
    for match in re.finditer(url_pattern, text):
        url = match.group(0)
        # Filter out likely non-citation URLs
        if any(domain in url for domain in ['doi.org', 'arxiv.org', 'pubmed', 'scholar.google']):
            citations.append({
                "type": "url",
                "value": url,
                "position": match.start(),
                "context": text[max(0, match.start()-30):match.end()+30]
            })
    
    # Numbered citations [1], (Smith, 2020), etc.
    numbered_pattern = r'\[(\d+)\]'
    for match in re.finditer(numbered_pattern, text):
        citations.append({
            "type": "numbered",
            "value": match.group(1),
            "position": match.start(),
            "context": text[max(0, match.start()-30):match.end()+30]
        })
    
    return citations


def _generate_content_outline(text: str, headings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate a hierarchical outline of the content."""
    outline = []
    
    if headings:
        # Use headings to create outline
        for heading in headings:
            outline.append({
                "level": heading["level"],
                "title": heading["title"],
                "type": "heading",
                "line_number": heading["line_number"]
            })
    else:
        # Create outline based on paragraph structure
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        for i, para in enumerate(paragraphs[:10]):  # Limit to first 10 paragraphs
            if len(para) > 50:  # Substantial paragraphs only
                # Use first sentence as title
                first_sentence = para.split('.')[0]
                if len(first_sentence) > 100:
                    first_sentence = first_sentence[:100] + "..."
                
                outline.append({
                    "level": 1,
                    "title": first_sentence,
                    "type": "paragraph",
                    "content_preview": para[:200] + "..." if len(para) > 200 else para
                })
    
    return outline


def _classify_content(text: str, url: str, title: str) -> Dict[str, Any]:
    """Classify content type and characteristics."""
    classification = {
        "primary_type": "unknown",
        "secondary_types": [],
        "confidence": 0.0,
        "characteristics": []
    }
    
    # Classification patterns
    academic_indicators = [
        "abstract", "methodology", "references", "doi:", "arxiv:", "journal",
        "university", "research", "study", "analysis", "findings", "conclusion"
    ]
    
    news_indicators = [
        "breaking", "reported", "according to", "sources say", "journalist",
        "correspondent", "news", "today", "yesterday", "latest"
    ]
    
    blog_indicators = [
        "posted by", "written by", "author", "blog", "personal", "opinion",
        "thoughts", "experience", "journey", "tutorial", "guide"
    ]
    
    documentation_indicators = [
        "documentation", "api", "reference", "manual", "guide", "tutorial",
        "installation", "configuration", "usage", "examples"
    ]
    
    text_lower = text.lower()
    url_lower = url.lower()
    title_lower = title.lower()
    
    # Score each type
    scores = {}
    
    # Academic content
    academic_score = sum(1 for indicator in academic_indicators
                        if indicator in text_lower or indicator in url_lower)
    scores["academic"] = academic_score / len(academic_indicators)
    
    # News content
    news_score = sum(1 for indicator in news_indicators
                    if indicator in text_lower or indicator in url_lower)
    scores["news"] = news_score / len(news_indicators)
    
    # Blog content
    blog_score = sum(1 for indicator in blog_indicators
                    if indicator in text_lower or indicator in url_lower)
    scores["blog"] = blog_score / len(blog_indicators)
    
    # Documentation
    doc_score = sum(1 for indicator in documentation_indicators
                   if indicator in text_lower or indicator in url_lower)
    scores["documentation"] = doc_score / len(documentation_indicators)
    
    # Determine primary type
    if scores:
        primary_type = max(scores.items(), key=lambda x: x[1])[0]
        confidence = scores[primary_type]
        
        classification["primary_type"] = primary_type
        classification["confidence"] = confidence
        
        # Add secondary types with significant scores
        for content_type, score in scores.items():
            if content_type != primary_type and score > 0.1:
                classification["secondary_types"].append({
                    "type": content_type,
                    "score": score
                })
    
    # Additional characteristics
    characteristics = []
    
    if len(text) > 5000:
        characteristics.append("long_form")
    elif len(text) < 1000:
        characteristics.append("short_form")
    
    if text.count('\n\n') > 10:
        characteristics.append("well_structured")
    
    if re.search(r'\d{4}', text):  # Contains years
        characteristics.append("time_referenced")
    
    if len(re.findall(r'https?://[^\s]+', text)) > 5:
        characteristics.append("link_heavy")
    
    classification["characteristics"] = characteristics
    
    return classification


def _extract_enhanced_metadata(text: str, url: str, title: str) -> Dict[str, Any]:
    """Extract enhanced metadata including dates, authors, categories."""
    metadata = {}
    
    # Extract publication dates
    date_patterns = [
        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{4})\b',  # MM/DD/YYYY or MM-DD-YYYY
        r'\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b',  # YYYY/MM/DD or YYYY-MM-DD
        r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\b',
        r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})\b'
    ]
    
    dates_found = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        dates_found.extend(matches)
    
    metadata["dates_found"] = dates_found[:5]  # Limit to first 5 dates
    
    # Extract author information
    author_patterns = [
        r'\bby\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',  # "by John Smith"
        r'\bauthor[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',  # "Author: John Smith"
        r'\bwritten\s+by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',  # "written by John Smith"
    ]
    
    authors_found = []
    for pattern in author_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        authors_found.extend(matches)
    
    metadata["authors_found"] = list(set(authors_found))[:3]  # Unique authors, limit to 3
    
    # Extract keywords and topics
    # Simple keyword extraction based on capitalized terms and common academic terms
    capitalized_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    # Filter common words
    common_words = {'The', 'This', 'That', 'These', 'Those', 'And', 'But', 'Or', 'For', 'With'}
    keywords = [term for term in set(capitalized_terms) if term not in common_words and len(term) > 3]
    metadata["potential_keywords"] = keywords[:10]  # Top 10 keywords
    
    # Extract numerical data and statistics
    numbers = re.findall(r'\b\d+(?:\.\d+)?%?\b', text)
    metadata["numerical_data_count"] = len(numbers)
    
    # Detect reading time (approximate)
    word_count = len(text.split())
    reading_time_minutes = max(1, word_count // 200)  # 200 words per minute
    metadata["estimated_reading_time"] = f"{reading_time_minutes} minute{'s' if reading_time_minutes > 1 else ''}"
    
    return metadata


def _is_academic_content(text: str, url: str) -> bool:
    """Check if content appears to be academic."""
    academic_domains = ['edu', 'ac.uk', 'arxiv.org', 'pubmed', 'scholar.google']
    if any(domain in url for domain in academic_domains):
        return True
    
    academic_indicators = ['abstract', 'methodology', 'references', 'doi:', 'journal']
    text_lower = text.lower()
    score = sum(1 for indicator in academic_indicators if indicator in text_lower)
    return score >= 2


def _is_news_content(text: str, url: str) -> bool:
    """Check if content appears to be news."""
    news_domains = ['news', 'reuters', 'bbc', 'cnn', 'ap', 'npr', 'times']
    if any(domain in url for domain in news_domains):
        return True
    
    news_indicators = ['breaking', 'reported', 'journalist', 'correspondent']
    text_lower = text.lower()
    score = sum(1 for indicator in news_indicators if indicator in text_lower)
    return score >= 1