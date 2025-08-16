"""
Reader agent module for fetching and processing web content.
Coordinates content extraction from URLs and manages text processing.
"""

import asyncio
from typing import List, Dict, Any, Optional
from ..tools.fetch_url import run as fetch_url_run
from ..tools.parse_pdf import run as parse_pdf_run
from ..observability.logging import get_logger
from ..observability.tracing import start_span, end_span

logger = get_logger(__name__)


class Reader:
    """Content reading agent that fetches and processes documents."""
    
    def __init__(self):
        self.max_concurrent_fetches = 5
        self.max_content_length = 50000  # Limit content per document
        self.chunk_size = 2000  # Size for text chunking
        self.chunk_overlap = 200  # Overlap between chunks
    
    async def read(self, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fetch and process content from search results.
        
        Args:
            search_results: List of search results with URLs
        
        Returns:
            Dict containing processed documents and chunks
        """
        span_id = start_span("read", "agent", {
            "url_count": len(search_results)
        })
        
        try:
            logger.info(f"Reading content from {len(search_results)} URLs")
            
            # Extract unique URLs from search results
            urls_to_fetch = []
            for result in search_results:
                url = result.get("url")
                if url and url not in [item["url"] for item in urls_to_fetch]:
                    urls_to_fetch.append({
                        "url": url,
                        "title": result.get("title", ""),
                        "snippet": result.get("snippet", ""),
                        "domain": result.get("domain", "")
                    })
            
            # Fetch content concurrently in batches
            all_documents = []
            
            for i in range(0, len(urls_to_fetch), self.max_concurrent_fetches):
                batch = urls_to_fetch[i:i + self.max_concurrent_fetches]
                batch_documents = await self._fetch_content_batch(batch)
                all_documents.extend(batch_documents)
            
            # Process successful documents
            processed_documents = []
            all_chunks = []
            
            for doc in all_documents:
                if doc["success"] and doc.get("text"):
                    # Process and chunk the document
                    processed_doc = self._process_document(doc)
                    chunks = self._create_chunks(processed_doc)
                    
                    processed_documents.append(processed_doc)
                    all_chunks.extend(chunks)
            
            # Calculate metrics
            successful_fetches = len(processed_documents)
            total_attempts = len(urls_to_fetch)
            total_chunks = len(all_chunks)
            total_text_length = sum(len(doc.get("text", "")) for doc in processed_documents)
            
            result = {
                "source_urls": [item["url"] for item in urls_to_fetch],
                "documents": processed_documents,
                "chunks": all_chunks,
                "metrics": {
                    "total_urls": total_attempts,
                    "successful_fetches": successful_fetches,
                    "fetch_success_rate": successful_fetches / max(total_attempts, 1),
                    "total_chunks": total_chunks,
                    "total_text_length": total_text_length,
                    "average_text_length": total_text_length / max(successful_fetches, 1)
                },
                "success": successful_fetches > 0
            }
            
            logger.info(f"Content reading completed: {successful_fetches}/{total_attempts} URLs successful, {total_chunks} chunks created")
            end_span(span_id, success=True, additional_data={
                "successful_fetches": successful_fetches,
                "total_chunks": total_chunks
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Content reading failed: {e}"
            logger.error(error_msg)
            end_span(span_id, success=False, error=error_msg)
            return {
                "source_urls": [],
                "documents": [],
                "chunks": [],
                "metrics": {
                    "total_urls": 0,
                    "successful_fetches": 0,
                    "fetch_success_rate": 0,
                    "total_chunks": 0,
                    "total_text_length": 0,
                    "average_text_length": 0
                },
                "success": False,
                "error": str(e)
            }
    
    async def _fetch_content_batch(self, url_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fetch content from a batch of URLs concurrently.
        
        Args:
            url_items: Batch of URL items to fetch
        
        Returns:
            List of fetched content results
        """
        tasks = []
        for item in url_items:
            url = item["url"]
            
            # Determine content type and use appropriate tool
            if url.lower().endswith('.pdf'):
                task = self._fetch_pdf_content(item)
            else:
                task = self._fetch_web_content(item)
            
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                formatted_results.append({
                    "url": url_items[i]["url"],
                    "success": False,
                    "error": str(result),
                    "title": url_items[i].get("title", ""),
                    "domain": url_items[i].get("domain", "")
                })
            else:
                formatted_results.append(result)
        
        return formatted_results
    
    async def _fetch_web_content(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch content from a web URL."""
        result = await fetch_url_run(item["url"], extract_text=True)
        
        # Enhance with search result metadata
        if result["success"]:
            result["search_title"] = item.get("title", "")
            result["search_snippet"] = item.get("snippet", "")
            result["domain"] = item.get("domain", "")
        
        return result
    
    async def _fetch_pdf_content(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch and parse PDF content."""
        result = await parse_pdf_run(item["url"], extract_metadata=True)
        
        # Enhance with search result metadata
        if result["success"]:
            result["search_title"] = item.get("title", "")
            result["search_snippet"] = item.get("snippet", "")
            result["domain"] = item.get("domain", "")
            result["content_type"] = "application/pdf"
        
        return result
    
    def _process_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and clean document content.
        
        Args:
            doc: Raw document from fetch operation
        
        Returns:
            Processed document with cleaned content
        """
        text = doc.get("text", "")
        
        # Limit content length
        if len(text) > self.max_content_length:
            text = text[:self.max_content_length]
            doc["truncated"] = True
        
        # Basic text cleaning
        text = self._clean_text(text)
        
        processed_doc = {
            "url": doc["url"],
            "title": doc.get("title") or doc.get("search_title", ""),
            "domain": doc.get("domain", ""),
            "text": text,
            "text_length": len(text),
            "content_type": doc.get("content_type", "text/html"),
            "fetch_timestamp": doc.get("timestamp"),
            "truncated": doc.get("truncated", False)
        }
        
        # Add metadata if available
        if "metadata" in doc:
            processed_doc["metadata"] = doc["metadata"]
        
        return processed_doc
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.
        
        Args:
            text: Raw text content
        
        Returns:
            Cleaned text
        """
        # Basic text cleaning
        import re
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
        
        # Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        return text.strip()
    
    def _create_chunks(self, doc: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create text chunks from document for better processing.
        
        Args:
            doc: Processed document
        
        Returns:
            List of text chunks
        """
        text = doc["text"]
        if not text:
            return []
        
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            
            # Try to break at sentence or word boundary
            if end < len(text):
                # Look for sentence boundary
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start + self.chunk_size // 2:
                    end = sentence_end + 1
                else:
                    # Look for word boundary
                    word_end = text.rfind(' ', start, end)
                    if word_end > start + self.chunk_size // 2:
                        end = word_end
            
            chunk_text = text[start:end].strip()
            
            if chunk_text:
                chunk = {
                    "chunk_id": f"{doc['url']}#{chunk_id}",
                    "document_url": doc["url"],
                    "document_title": doc["title"],
                    "text": chunk_text,
                    "text_length": len(chunk_text),
                    "start_position": start,
                    "end_position": end,
                    "chunk_index": chunk_id
                }
                chunks.append(chunk)
                chunk_id += 1
            
            # Move start position with overlap
            start = max(start + 1, end - self.chunk_overlap)
            
            # Prevent infinite loop
            if start >= end:
                break
        
        return chunks


# Global reader instance
reader = Reader()


async def read(search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convenience function for content reading."""
    return await reader.read(search_results)