"""PDF parsing tool for Nova Brief."""

from typing import Dict, Any, Optional, Union
import io
import httpx
from ..observability.logging import get_logger
from ..observability.tracing import TimedOperation, emit_event

logger = get_logger(__name__)


async def run(
    source: Union[str, bytes],
    max_pages: Optional[int] = None,
    timeout: float = 15.0
) -> Dict[str, Any]:
    """
    Parse PDF content from URL or bytes.
    
    Args:
        source: PDF URL or raw bytes
        max_pages: Maximum number of pages to process
        timeout: Request timeout if source is URL
    
    Returns:
        Dictionary with success status, extracted text, and metadata
    """
    with TimedOperation("parse_pdf") as timer:
        try:
            # Import here to handle missing dependency gracefully
            from pypdf import PdfReader
            
            pdf_bytes = None
            source_type = "bytes" if isinstance(source, bytes) else "url"
            
            if isinstance(source, str):
                # Fetch PDF from URL
                logger.info(f"Fetching PDF from URL: {source}")
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(source)
                    response.raise_for_status()
                    
                    content_type = response.headers.get("content-type", "").lower()
                    if "application/pdf" not in content_type:
                        return {
                            "success": False,
                            "error": f"Not a PDF: {content_type}",
                            "source": source
                        }
                    
                    pdf_bytes = response.content
            else:
                pdf_bytes = source
            
            if not pdf_bytes:
                return {
                    "success": False,
                    "error": "No PDF data provided",
                    "source": str(source)
                }
            
            # Parse PDF content
            logger.info(f"Parsing PDF: {len(pdf_bytes)} bytes")
            
            pdf_stream = io.BytesIO(pdf_bytes)
            reader = PdfReader(pdf_stream)
            
            # Extract metadata
            metadata = {
                "source": str(source),
                "source_type": source_type,
                "total_pages": len(reader.pages),
                "size_bytes": len(pdf_bytes)
            }
            
            # Extract PDF info if available
            if reader.metadata:
                pdf_info = dict(reader.metadata)
                metadata.update({
                    "title": pdf_info.get("/Title", ""),
                    "author": pdf_info.get("/Author", ""),
                    "subject": pdf_info.get("/Subject", ""),
                    "creator": pdf_info.get("/Creator", ""),
                    "producer": pdf_info.get("/Producer", ""),
                    "creation_date": str(pdf_info.get("/CreationDate", "")),
                    "modification_date": str(pdf_info.get("/ModDate", ""))
                })
            
            # Determine pages to process
            total_pages = len(reader.pages)
            pages_to_process = min(max_pages or total_pages, total_pages)
            
            # Extract text from pages
            extracted_text = ""
            processed_pages = 0
            
            for page_num in range(pages_to_process):
                try:
                    page = reader.pages[page_num]
                    page_text = page.extract_text()
                    
                    if page_text.strip():
                        extracted_text += f"\n--- Page {page_num + 1} ---\n"
                        extracted_text += page_text.strip()
                        extracted_text += "\n"
                    
                    processed_pages += 1
                    
                except Exception as e:
                    logger.warning(f"Error extracting text from page {page_num + 1}: {e}")
                    continue
            
            metadata.update({
                "processed_pages": processed_pages,
                "text_length": len(extracted_text)
            })
            
            if not extracted_text.strip():
                logger.warning(f"No text extracted from PDF: {source}")
                return {
                    "success": False,
                    "error": "NO_TEXT_EXTRACTED",
                    "source": str(source),
                    "metadata": metadata
                }
            
            logger.info(
                f"PDF parsed successfully: {processed_pages} pages, {len(extracted_text)} chars",
                extra={
                    "source": str(source),
                    "total_pages": total_pages,
                    "processed_pages": processed_pages,
                    "text_length": len(extracted_text)
                }
            )
            
            emit_event(
                "pdf_parsed",
                metadata={
                    "source_type": source_type,
                    "total_pages": total_pages,
                    "processed_pages": processed_pages,
                    "text_length": len(extracted_text),
                    "has_metadata": bool(reader.metadata)
                }
            )
            
            return {
                "success": True,
                "source": str(source),
                "text": extracted_text.strip(),
                "metadata": metadata
            }
            
        except ImportError:
            logger.error("pypdf package not installed")
            return {
                "success": False,
                "error": "PDF_PARSER_UNAVAILABLE",
                "source": str(source)
            }
        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching PDF: {source}")
            return {
                "success": False,
                "error": "TIMEOUT",
                "source": str(source)
            }
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error fetching PDF {source}: {e.response.status_code}")
            return {
                "success": False,
                "error": f"HTTP_{e.response.status_code}",
                "source": str(source)
            }
        except Exception as e:
            logger.error(f"Error parsing PDF from {source}: {e}")
            emit_event(
                "pdf_parse_error",
                metadata={
                    "source": str(source),
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "source": str(source)
            }


def extract_text_from_bytes(pdf_bytes: bytes, max_pages: Optional[int] = None) -> str:
    """
    Convenience function to extract text from PDF bytes.
    
    Args:
        pdf_bytes: PDF file as bytes
        max_pages: Maximum pages to process
    
    Returns:
        Extracted text content
    """
    import asyncio
    
    async def _extract():
        result = await run(pdf_bytes, max_pages=max_pages)
        return result.get("text", "") if result.get("success") else ""
    
    return asyncio.run(_extract())