"""
PDF parsing tool for extracting text content from PDF documents.
Handles both local files and URLs pointing to PDFs.
"""

import asyncio
import os
import tempfile
from typing import Dict, Any, Optional, Union
from pathlib import Path
import httpx
from pypdf import PdfReader
from ..observability.logging import get_logger
from ..observability.tracing import start_span, end_span

logger = get_logger(__name__)


class ParsePdfTool:
    """Tool for parsing PDF documents and extracting text."""
    
    def __init__(self):
        self.timeout = int(os.getenv("FETCH_TIMEOUT_S", "15"))
        self.user_agent = os.getenv("USER_AGENT", "NovaBrief-Research/0.1")
        self.max_file_size = 50 * 1024 * 1024  # 50MB limit
        self.max_pages = 100  # Limit pages to prevent excessive processing
    
    async def run(self, source: Union[str, Path], extract_metadata: bool = True) -> Dict[str, Any]:
        """
        Parse PDF and extract text content.
        
        Args:
            source: File path or URL to PDF
            extract_metadata: Whether to extract PDF metadata
        
        Returns:
            Dict with extracted text, metadata, and status
        """
        span_id = start_span("parse_pdf", "tools", {"source": str(source)})
        
        try:
            # Determine if source is URL or file path
            if isinstance(source, str) and (source.startswith("http://") or source.startswith("https://")):
                # Download PDF from URL
                pdf_path = await self._download_pdf(source)
                is_temp_file = True
            else:
                # Use local file
                pdf_path = Path(source)
                is_temp_file = False
                
                if not pdf_path.exists():
                    raise FileNotFoundError(f"PDF file not found: {source}")
            
            logger.info(f"Parsing PDF: {pdf_path}")
            
            # Parse PDF
            result = await self._parse_pdf_file(pdf_path, extract_metadata)
            result["source"] = str(source)
            result["success"] = True
            
            # Clean up temp file if needed
            if is_temp_file:
                pdf_path.unlink(missing_ok=True)
            
            logger.info(f"Successfully parsed PDF: {result.get('page_count', 0)} pages, {result.get('text_length', 0)} characters")
            end_span(span_id, success=True, additional_data={
                "page_count": result.get("page_count", 0),
                "text_length": result.get("text_length", 0)
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to parse PDF {source}: {e}"
            logger.error(error_msg)
            end_span(span_id, success=False, error=error_msg)
            return {
                "source": str(source),
                "success": False,
                "error": "parse_error",
                "error_message": error_msg
            }
    
    async def _download_pdf(self, url: str) -> Path:
        """
        Download PDF from URL to temporary file.
        
        Args:
            url: URL to PDF
        
        Returns:
            Path to downloaded file
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "application/pdf,*/*"
                },
                follow_redirects=True
            )
            
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get("content-type", "").lower()
            if "application/pdf" not in content_type:
                logger.warning(f"URL may not be a PDF: {content_type}")
            
            # Check file size
            content_length = len(response.content)
            if content_length > self.max_file_size:
                raise ValueError(f"PDF too large: {content_length} bytes")
            
            # Save to temporary file
            temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
            temp_file.write(response.content)
            temp_file.close()
            
            return Path(temp_file.name)
    
    async def _parse_pdf_file(self, pdf_path: Path, extract_metadata: bool) -> Dict[str, Any]:
        """
        Parse PDF file and extract text and metadata.
        
        Args:
            pdf_path: Path to PDF file
            extract_metadata: Whether to extract metadata
        
        Returns:
            Dict with extracted content
        """
        def _extract_text():
            """Synchronous PDF text extraction."""
            with open(pdf_path, 'rb') as file:
                reader = PdfReader(file)
                
                result = {
                    "page_count": len(reader.pages),
                    "pages": [],
                    "text": "",
                    "text_length": 0
                }
                
                # Extract metadata if requested
                if extract_metadata and reader.metadata:
                    metadata = {}
                    for key, value in reader.metadata.items():
                        if key.startswith('/'):
                            clean_key = key[1:].lower()
                            metadata[clean_key] = str(value) if value else None
                    result["metadata"] = metadata
                
                # Extract text from pages
                full_text = []
                pages_to_process = min(len(reader.pages), self.max_pages)
                
                for i in range(pages_to_process):
                    try:
                        page = reader.pages[i]
                        page_text = page.extract_text()
                        
                        page_info = {
                            "page_number": i + 1,
                            "text": page_text,
                            "text_length": len(page_text)
                        }
                        
                        result["pages"].append(page_info)
                        full_text.append(page_text)
                        
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {i + 1}: {e}")
                        result["pages"].append({
                            "page_number": i + 1,
                            "text": "",
                            "text_length": 0,
                            "error": str(e)
                        })
                
                # Combine all text
                result["text"] = "\n\n".join(full_text)
                result["text_length"] = len(result["text"])
                
                if pages_to_process < len(reader.pages):
                    result["truncated"] = True
                    result["total_pages"] = len(reader.pages)
                
                return result
        
        # Run in thread pool to avoid blocking
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(executor, _extract_text)


# Global tool instance
parse_pdf_tool = ParsePdfTool()


async def run(source: Union[str, Path], extract_metadata: bool = True) -> Dict[str, Any]:
    """Convenience function for PDF parsing."""
    return await parse_pdf_tool.run(source, extract_metadata)


def run_sync(source: Union[str, Path], extract_metadata: bool = True) -> Dict[str, Any]:
    """Synchronous wrapper for PDF parsing."""
    return asyncio.run(run(source, extract_metadata))