"""Data models and type definitions for Nova Brief."""

from typing import Dict, List, Optional, Any, Union, TypedDict
from dataclasses import dataclass
from datetime import datetime


# Type definitions for MVP (using TypedDict)
class SearchResult(TypedDict):
    """Search result from web search providers."""
    title: str
    url: str
    snippet: str


class Document(TypedDict):
    """Document fetched and processed from a URL."""
    url: str
    title: str
    text: str
    content_type: str
    source_meta: Dict[str, Any]


class Chunk(TypedDict):
    """Text chunk for processing by the analyst."""
    doc_url: str
    text: str
    hash: str
    tokens: int
    chunk_index: int


class Claim(TypedDict):
    """Claim extracted by the analyst."""
    id: str
    text: str
    type: str  # fact, estimate, opinion
    confidence: float  # 0.0 to 1.0
    source_urls: List[str]


class Citation(TypedDict):
    """Citation linking claims to sources."""
    claim_id: str
    urls: List[str]
    citation_number: Optional[int]


class Reference(TypedDict):
    """Reference entry for the final report."""
    number: int
    url: str
    title: Optional[str]
    access_date: Optional[str]


class Metrics(TypedDict):
    """Performance and cost metrics."""
    duration_s: float
    tokens_in: int
    tokens_out: int
    cost_est: float
    sources_count: int
    domain_diversity: int
    cache_hits: int
    cache_misses: int
    search_queries: int
    urls_fetched: int
    urls_failed: int


class Constraints(TypedDict):
    """Research constraints and configuration."""
    date_range: Optional[str]
    include_domains: List[str]
    exclude_domains: List[str]
    max_rounds: int
    per_domain_cap: int
    fetch_timeout_s: float
    max_tokens_per_chunk: int


class ResearchState(TypedDict):
    """Complete state object passed through the agent pipeline."""
    topic: str
    constraints: Constraints
    sub_questions: List[str]
    queries: List[str]
    search_results: List[SearchResult]
    documents: List[Document]
    chunks: List[Chunk]
    claims: List[Claim]
    citations: List[Citation]
    draft_sections: List[str]
    final_report: Optional[Dict[str, Any]]
    metrics: Metrics
    current_round: int
    status: str  # planning, searching, reading, analyzing, verifying, writing, complete


class Report(TypedDict):
    """Final research report."""
    topic: str
    report_md: str
    references: List[Reference]
    metadata: Dict[str, Any]
    sections: List[str]
    word_count: int
    created_at: str


# Utility functions for creating default instances
def create_default_constraints() -> Constraints:
    """Create default constraints configuration."""
    return {
        "date_range": None,
        "include_domains": [],
        "exclude_domains": [],
        "max_rounds": 3,
        "per_domain_cap": 3,
        "fetch_timeout_s": 15.0,
        "max_tokens_per_chunk": 1000
    }


def create_default_metrics() -> Metrics:
    """Create default metrics object."""
    return {
        "duration_s": 0.0,
        "tokens_in": 0,
        "tokens_out": 0,
        "cost_est": 0.0,
        "sources_count": 0,
        "domain_diversity": 0,
        "cache_hits": 0,
        "cache_misses": 0,
        "search_queries": 0,
        "urls_fetched": 0,
        "urls_failed": 0
    }


def create_initial_state(topic: str, constraints: Optional[Constraints] = None) -> ResearchState:
    """Create initial research state for a topic."""
    return {
        "topic": topic,
        "constraints": constraints or create_default_constraints(),
        "sub_questions": [],
        "queries": [],
        "search_results": [],
        "documents": [],
        "chunks": [],
        "claims": [],
        "citations": [],
        "draft_sections": [],
        "final_report": None,
        "metrics": create_default_metrics(),
        "current_round": 0,
        "status": "planning"
    }


# Data validation helpers
def validate_search_result(result: Dict[str, Any]) -> bool:
    """Validate a search result dictionary."""
    required_fields = {"title", "url", "snippet"}
    return all(field in result and isinstance(result[field], str) for field in required_fields)


def validate_claim(claim: Dict[str, Any]) -> bool:
    """Validate a claim dictionary."""
    required_fields = {"id", "text", "type", "confidence"}
    if not all(field in claim for field in required_fields):
        return False
    
    if not isinstance(claim["confidence"], (int, float)) or not 0.0 <= claim["confidence"] <= 1.0:
        return False
    
    if claim["type"] not in {"fact", "estimate", "opinion"}:
        return False
    
    return True


def validate_document(document: Dict[str, Any]) -> bool:
    """Validate a document dictionary."""
    required_fields = {"url", "title", "text", "content_type", "source_meta"}
    return all(field in document for field in required_fields)


# Content chunking utilities
def create_chunks_from_document(
    document: Document,
    max_tokens_per_chunk: int = 1000,
    overlap_tokens: int = 100
) -> List[Chunk]:
    """
    Split document text into chunks for processing.
    
    Args:
        document: Document to chunk
        max_tokens_per_chunk: Maximum tokens per chunk
        overlap_tokens: Overlap between chunks
    
    Returns:
        List of text chunks
    """
    text = document["text"]
    if not text:
        return []
    
    # Simple word-based chunking (approximate tokens)
    words = text.split()
    chunks = []
    chunk_index = 0
    
    # Rough approximation: 1 token ≈ 0.75 words
    words_per_chunk = int(max_tokens_per_chunk * 0.75)
    overlap_words = int(overlap_tokens * 0.75)
    
    start = 0
    while start < len(words):
        end = min(start + words_per_chunk, len(words))
        chunk_text = " ".join(words[start:end])
        
        if chunk_text.strip():
            chunk_hash = str(hash(chunk_text))
            chunks.append({
                "doc_url": document["url"],
                "text": chunk_text,
                "hash": chunk_hash,
                "tokens": len(chunk_text.split()),  # Rough token estimate
                "chunk_index": chunk_index
            })
            chunk_index += 1
        
        start = max(start + words_per_chunk - overlap_words, start + 1)
        if start >= len(words):
            break
    
    return chunks


def estimate_tokens(text: str) -> int:
    """Rough token estimation based on word count."""
    if not text:
        return 0
    return int(len(text.split()) / 0.75)  # Approximate conversion