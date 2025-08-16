"""
URL fetching and content extraction tool.
Handles web page fetching with robust error handling and content extraction.
"""

import asyncio
import os
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import httpx
import trafilatura
from ..observability.logging import get_logger
from ..observability.tracing import start_span, end_span

logger = get_logger(__name__)


class FetchUrlTool:
    """Tool for fetching and extracting content from URLs."""
    
    def __init__(self):
        self.timeout = int(os.getenv("FETCH_TIMEOUT_S", "15"))
        self.user_agent = os.getenv("USER_AGENT", "NovaBrief-Research/0.1")
        self.max_content_length = 10 * 1024 * 1024  # 10MB limit
    
    async def run(self, url: str, extract_text: bool = True) -> Dict[str, Any]:
        """
        Fetch URL and optionally extract main content.
        
        Args:
            url: URL to fetch
            extract_text: Whether to extract main text content
        
        Returns:
            Dict with content, metadata, and status
        """
        span_id = start_span("fetch_url", "tools", {"url": url})
        
        try:
            # Validate URL
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError(f"Invalid URL: {url}")
            
            logger.info(f"Fetching URL: {url}")
            
            # Fetch content
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept-Encoding": "gzip, deflate",
                        "DNT": "1",
                        "Connection": "keep-alive"
                    },
                    follow_redirects=True
                )
                
                response.raise_for_status()
                
                # Check content length
                content_length = len(response.content)
                if content_length > self.max_content_length:
                    raise ValueError(f"Content too large: {content_length} bytes")
                
                # Get content type
                content_type = response.headers.get("content-type", "").lower()
                
                result = {
                    "url": str(response.url),  # Final URL after redirects
                    "original_url": url,
                    "status_code": response.status_code,
                    "content_type": content_type,
                    "content_length": content_length,
                    "success": True
                }
                
                # Extract text content if requested and content is HTML
                if extract_text and "text/html" in content_type:
                    try:
                        # Use trafilatura for main content extraction
                        extracted_text = trafilatura.extract(
                            response.text,
                            include_comments=False,
                            include_tables=True,
                            include_formatting=False
                        )
                        
                        if extracted_text:
                            result["text"] = extracted_text
                            result["text_length"] = len(extracted_text)
                            
                            # Extract metadata
                            metadata = trafilatura.extract_metadata(response.text)
                            if metadata:
                                result["title"] = metadata.title
                                result["author"] = metadata.author
                                result["date"] = metadata.date
                                result["description"] = metadata.description
                        else:
                            result["text"] = ""
                            result["text_length"] = 0
                            logger.warning(f"No text extracted from {url}")
                    
                    except Exception as e:
                        logger.error(f"Text extraction failed for {url}: {e}")
                        result["text"] = ""
                        result["text_length"] = 0
                        result["extraction_error"] = str(e)
                
                # Store raw content for non-HTML or if extraction is disabled
                if not extract_text or "text/html" not in content_type:
                    result["raw_content"] = response.text[:50000]  # Limit raw content
                
                logger.info(f"Successfully fetched {url}: {content_length} bytes")
                end_span(span_id, success=True, additional_data={
                    "content_length": content_length,
                    "content_type": content_type,
                    "status_code": response.status_code
                })
                
                return result
                
        except httpx.TimeoutException:
            error_msg = f"Timeout fetching {url}"
            logger.error(error_msg)
            end_span(span_id, success=False, error=error_msg)
            return {
                "url": url,
                "original_url": url,
                "success": False,
                "error": "timeout",
                "error_message": error_msg
            }
        
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP {e.response.status_code} for {url}"
            logger.error(error_msg)
            end_span(span_id, success=False, error=error_msg)
            return {
                "url": url,
                "original_url": url,
                "success": False,
                "error": "http_error",
                "error_message": error_msg,
                "status_code": e.response.status_code
            }
        
        except Exception as e:
            error_msg = f"Failed to fetch {url}: {e}"
            logger.error(error_msg)
            end_span(span_id, success=False, error=error_msg)
            return {
                "url": url,
                "original_url": url,
                "success": False,
                "error": "fetch_error",
                "error_message": error_msg
            }


# Global tool instance
fetch_url_tool = FetchUrlTool()


async def run(url: str, extract_text: bool = True) -> Dict[str, Any]:
    """Convenience function for URL fetching."""
    return await fetch_url_tool.run(url, extract_text)


def run_sync(url: str, extract_text: bool = True) -> Dict[str, Any]:
    """Synchronous wrapper for URL fetching."""
    return asyncio.run(run(url, extract_text))