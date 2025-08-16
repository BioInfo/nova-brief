"""URL fetching and HTML content extraction for Nova Brief."""

import os
from typing import Dict, Any, Optional
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import trafilatura

from ..observability.logging import get_logger
from ..observability.tracing import TimedOperation, emit_event

logger = get_logger(__name__)


class RobotsTxtChecker:
    """Utility for checking robots.txt compliance."""
    
    def __init__(self):
        self._cache = {}
    
    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """
        Check if URL can be fetched according to robots.txt.
        
        Args:
            url: URL to check
            user_agent: User agent string
        
        Returns:
            True if allowed, False if disallowed
        """
        try:
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            robots_url = urljoin(base_url, "/robots.txt")
            
            if robots_url not in self._cache:
                rp = RobotFileParser()
                rp.set_url(robots_url)
                try:
                    rp.read()
                    self._cache[robots_url] = rp
                except Exception:
                    # If robots.txt can't be fetched, assume allowed
                    self._cache[robots_url] = None
            
            rp = self._cache[robots_url]
            if rp is None:
                return True
            
            return rp.can_fetch(user_agent, url)
            
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {e}")
            return True  # Default to allowing if check fails


robots_checker = RobotsTxtChecker()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True
)
async def run(
    url: str,
    timeout: float = 15.0,
    user_agent: Optional[str] = None,
    respect_robots: bool = True,
    extract_content: bool = True
) -> Dict[str, Any]:
    """
    Fetch URL and extract main content.
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        user_agent: User agent string (defaults to env USER_AGENT)
        respect_robots: Whether to respect robots.txt
        extract_content: Whether to extract main content from HTML
    
    Returns:
        Dictionary with success status, extracted content, and metadata
    """
    if not user_agent:
        user_agent = os.getenv("USER_AGENT", "Nova-Brief Academic Research Agent/1.0 (+https://github.com/BioInfo/nova-brief; research@nova-brief.ai)")
    
    with TimedOperation(f"fetch_url") as timer:
        try:
            # Validate URL
            if not url or not url.startswith(('http://', 'https://')):
                return {
                    "success": False,
                    "error": "Invalid URL format",
                    "url": url
                }
            
            # Check robots.txt if required
            if respect_robots and not robots_checker.can_fetch(url, user_agent):
                logger.info(f"URL blocked by robots.txt: {url}")
                return {
                    "success": False,
                    "error": "ROBOTS_DISALLOWED",
                    "url": url
                }
            
            logger.info(f"Fetching URL: {url}")
            
            # Set up HTTP client
            headers = {
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, headers=headers, follow_redirects=True)
                response.raise_for_status()
                
                content_type = response.headers.get("content-type", "").lower()
                
                # Handle different content types
                if "text/html" in content_type or "application/xhtml" in content_type:
                    return await _process_html(url, response.text, extract_content)
                elif "application/pdf" in content_type:
                    return {
                        "success": True,
                        "url": url,
                        "content_type": "application/pdf",
                        "raw_content": response.content,
                        "text": "",  # PDF parsing handled separately
                        "title": "",
                        "metadata": {
                            "size_bytes": len(response.content),
                            "content_type": content_type
                        }
                    }
                else:
                    # Plain text or other content
                    text_content = response.text if hasattr(response, 'text') else str(response.content)
                    return {
                        "success": True,
                        "url": url,
                        "content_type": content_type,
                        "text": text_content[:50000],  # Limit plain text size
                        "title": "",
                        "metadata": {
                            "size_bytes": len(response.content),
                            "content_type": content_type
                        }
                    }
        
        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching URL: {url}")
            return {
                "success": False,
                "error": "TIMEOUT",
                "url": url
            }
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error fetching URL {url}: {e.response.status_code}")
            return {
                "success": False,
                "error": f"HTTP_{e.response.status_code}",
                "url": url
            }
        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}")
            emit_event(
                "url_fetch_error",
                metadata={
                    "url": url,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "url": url
            }


async def _process_html(url: str, html_content: str, extract_content: bool) -> Dict[str, Any]:
    """Process HTML content and extract main text."""
    try:
        if extract_content:
            # Use trafilatura for main content extraction
            extracted_text = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=True,
                include_formatting=False,
                url=url
            )
            
            # Extract title
            title = ""
            try:
                # Simple title extraction from HTML
                import re
                title_match = re.search(r'<title[^>]*>([^<]+)</title>', html_content, re.IGNORECASE)
                if title_match:
                    title = title_match.group(1).strip()
            except Exception:
                pass
            
            if not extracted_text:
                logger.warning(f"No content extracted from {url}")
                return {
                    "success": False,
                    "error": "NO_CONTENT_EXTRACTED",
                    "url": url
                }
        else:
            # Return raw HTML
            extracted_text = html_content
            title = ""
        
        result = {
            "success": True,
            "url": url,
            "content_type": "text/html",
            "text": extracted_text or "",
            "title": title,
            "metadata": {
                "size_bytes": len(html_content),
                "extracted_length": len(extracted_text) if extracted_text else 0,
                "content_type": "text/html"
            }
        }
        
        logger.info(
            f"HTML content extracted from {url}: {len(extracted_text or '')} chars",
            extra={
                "url": url,
                "title": title,
                "text_length": len(extracted_text or ''),
                "html_length": len(html_content)
            }
        )
        
        emit_event(
            "content_extracted",
            metadata={
                "url": url,
                "content_type": "text/html",
                "text_length": len(extracted_text or ''),
                "has_title": bool(title)
            }
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing HTML from {url}: {e}")
        return {
            "success": False,
            "error": f"HTML_PROCESSING_ERROR: {str(e)}",
            "url": url
        }