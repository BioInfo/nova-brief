"""Analyst component for synthesizing information and extracting claims."""

import uuid
import json
from typing import Dict, List, Any
from ..providers.openrouter_client import chat, create_json_schema_format
from ..storage.models import Document, Chunk, Claim, Citation
from ..observability.logging import get_logger
from ..observability.tracing import TimedOperation, emit_event

logger = get_logger(__name__)


ANALYSIS_SYSTEM_PROMPT = """You are a research analyst expert at synthesizing information from multiple sources. Your task is to:

1. Extract precise, verifiable claims from the provided content
2. Classify each claim as fact, estimate, or opinion
3. Assign confidence scores (0.0-1.0) based on evidence quality
4. Associate claims with their supporting source URLs
5. Identify areas needing additional research

Guidelines:
- Focus on specific, verifiable statements rather than general observations
- Prefer claims that can be backed by authoritative sources
- Mark estimates and opinions appropriately
- Higher confidence for facts from credible sources, lower for opinions
- Include diverse perspectives when available
- Flag claims that need stronger evidence

CRITICAL: You MUST respond with ONLY a valid JSON object in this exact format, with no additional text:
{
  "claims": [
    {
      "text": "specific verifiable claim",
      "type": "fact",
      "confidence": 0.85,
      "source_urls": ["https://example.com"]
    }
  ],
  "sections": ["Key Theme 1", "Key Theme 2"]
}

Do not include any text before or after the JSON. Only valid JSON."""


async def analyze(
    documents: List[Document],
    chunks: List[Chunk],
    sub_questions: List[str],
    topic: str
) -> Dict[str, Any]:
    """
    Analyze documents and chunks to extract claims and draft sections.
    
    Args:
        documents: List of processed documents
        chunks: List of text chunks for analysis
        sub_questions: Research sub-questions to address
        topic: Main research topic
    
    Returns:
        Dictionary with success status, claims, citations, and draft sections
    """
    with TimedOperation("agent_analyst") as timer:
        try:
            if not chunks:
                return {
                    "success": False,
                    "error": "No content chunks provided for analysis",
                    "claims": [],
                    "citations": [],
                    "draft_sections": []
                }
            
            logger.info(f"Analyzing {len(chunks)} chunks from {len(documents)} documents")
            
            # Group chunks by document for better context
            chunks_by_doc = _group_chunks_by_document(chunks)
            
            # Analyze in batches to handle large content volumes
            all_claims = []
            all_citations = []
            all_sections = []
            
            batch_size = 5  # Process 5 documents at a time
            doc_urls = list(chunks_by_doc.keys())
            
            for i in range(0, len(doc_urls), batch_size):
                batch_urls = doc_urls[i:i + batch_size]
                batch_result = await _analyze_document_batch(
                    batch_urls, 
                    chunks_by_doc, 
                    documents,
                    sub_questions, 
                    topic
                )
                
                if batch_result["success"]:
                    all_claims.extend(batch_result["claims"])
                    all_citations.extend(batch_result["citations"])
                    all_sections.extend(batch_result["sections"])
                else:
                    logger.warning(f"Batch analysis failed: {batch_result.get('error')}")
            
            # Deduplicate and merge similar claims
            final_claims, final_citations = _deduplicate_claims(all_claims, all_citations)
            
            # Create structured draft sections
            draft_sections = _create_draft_sections(final_claims, all_sections, topic)
            
            # Calculate analysis metrics
            confidence_scores = [claim["confidence"] for claim in final_claims]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            # Count claims by type
            claim_types = {}
            for claim in final_claims:
                claim_type = claim["type"]
                claim_types[claim_type] = claim_types.get(claim_type, 0) + 1
            
            # Calculate source diversity
            all_source_urls = set()
            for citation in final_citations:
                all_source_urls.update(citation["urls"])
            
            source_domains = set()
            for url in all_source_urls:
                try:
                    from urllib.parse import urlparse
                    domain = urlparse(url).netloc
                    source_domains.add(domain)
                except Exception:
                    continue
            
            metadata = {
                "documents_analyzed": len(documents),
                "chunks_analyzed": len(chunks),
                "claims_extracted": len(final_claims),
                "citations_created": len(final_citations),
                "avg_confidence": round(avg_confidence, 3),
                "claim_types": claim_types,
                "source_diversity": len(source_domains),
                "draft_sections": len(draft_sections)
            }
            
            logger.info(
                f"Analysis completed: {len(final_claims)} claims, {len(final_citations)} citations",
                extra=metadata
            )
            
            emit_event(
                "analysis_completed",
                metadata=metadata
            )
            
            return {
                "success": True,
                "claims": final_claims,
                "citations": final_citations,
                "draft_sections": draft_sections,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            emit_event(
                "analysis_error",
                metadata={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "documents_count": len(documents) if documents else 0,
                    "chunks_count": len(chunks) if chunks else 0
                }
            )
            
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "claims": [],
                "citations": [],
                "draft_sections": []
            }


async def _analyze_document_batch(
    doc_urls: List[str],
    chunks_by_doc: Dict[str, List[Chunk]],
    documents: List[Document],
    sub_questions: List[str],
    topic: str
) -> Dict[str, Any]:
    """Analyze a batch of documents using LLM."""
    try:
        # Prepare content summary for LLM
        doc_summaries = []
        
        for doc_url in doc_urls:
            doc_chunks = chunks_by_doc[doc_url]
            
            # Find document metadata
            doc_info = next((doc for doc in documents if doc["url"] == doc_url), None)
            doc_title = doc_info["title"] if doc_info else "Unknown"
            
            # Combine chunks for this document
            combined_text = "\n\n".join([chunk["text"] for chunk in doc_chunks])
            
            # Limit text length for LLM context
            if len(combined_text) > 4000:
                combined_text = combined_text[:4000] + "..."
            
            doc_summaries.append({
                "url": doc_url,
                "title": doc_title,
                "content": combined_text
            })
        
        # Prepare analysis prompt
        content_text = ""
        for i, doc_summary in enumerate(doc_summaries, 1):
            content_text += f"\n=== Source {i}: {doc_summary['title']} ===\n"
            content_text += f"URL: {doc_summary['url']}\n"
            content_text += f"Content: {doc_summary['content']}\n"
        
        user_prompt = f"""Research Topic: {topic}

Sub-questions to address:
{chr(10).join(f"- {q}" for q in sub_questions)}

Source Content:
{content_text}

Extract specific claims from this content, focusing on verifiable facts, estimates, and expert opinions. Associate each claim with its source URLs."""

        # Define JSON schema for structured output
        json_schema = {
            "type": "object",
            "properties": {
                "claims": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "type": {"type": "string", "enum": ["fact", "estimate", "opinion"]},
                            "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                            "source_urls": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["text", "type", "confidence", "source_urls"]
                    }
                },
                "sections": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Draft section headings or key themes identified"
                }
            },
            "required": ["claims", "sections"],
            "additionalProperties": False
        }
        
        # Call LLM for analysis
        messages = [
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        # Use prompt-based JSON instead of structured output (which fails on gpt-oss-120b)
        response = await chat(
            messages=messages,
            temperature=0.1,
            max_tokens=2000
        )
        
        if not response["success"]:
            return {
                "success": False,
                "error": f"LLM analysis failed: {response.get('error')}",
                "claims": [],
                "citations": [],
                "sections": []
            }
        
        # Parse LLM response with robust JSON extraction and repair
        try:
            content = response.get("content", "")
            if not content:
                raise ValueError("Empty response content")
            
            # Try multiple JSON parsing strategies
            analysis_result = _parse_json_response(content)
            raw_claims = analysis_result.get("claims", [])
            sections = analysis_result.get("sections", [])
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse analysis response: {e}")
            logger.error(f"Raw content: {content[:500]}...")
            
            # Fallback: try to extract individual claims using regex
            fallback_result = _extract_claims_fallback(content, doc_urls)
            if fallback_result["claims"]:
                logger.info(f"Fallback extraction recovered {len(fallback_result['claims'])} claims")
                return {
                    "success": True,
                    "claims": fallback_result["claims"],
                    "citations": fallback_result["citations"],
                    "sections": ["Analysis Results", "Key Findings"]
                }
            
            return {
                "success": False,
                "error": f"Response parsing failed: {str(e)}",
                "claims": [],
                "citations": [],
                "sections": []
            }
        
        # Process claims and create citations
        claims = []
        citations = []
        
        for raw_claim in raw_claims:
            try:
                claim_id = str(uuid.uuid4())[:8]
                
                claim: Claim = {
                    "id": claim_id,
                    "text": raw_claim["text"],
                    "type": raw_claim["type"],
                    "confidence": float(raw_claim["confidence"]),
                    "source_urls": raw_claim["source_urls"]
                }
                
                # Validate URLs are from our document set
                valid_urls = [url for url in raw_claim["source_urls"] if url in doc_urls]
                if valid_urls:
                    claim["source_urls"] = valid_urls
                    claims.append(claim)
                    
                    # Create citation
                    citation: Citation = {
                        "claim_id": claim_id,
                        "urls": valid_urls,
                        "citation_number": None  # Will be assigned later
                    }
                    citations.append(citation)
                
            except Exception as e:
                logger.warning(f"Error processing claim: {e}")
                continue
        
        return {
            "success": True,
            "claims": claims,
            "citations": citations,
            "sections": sections
        }
        
    except Exception as e:
        logger.error(f"Batch analysis failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "claims": [],
            "citations": [],
            "sections": []
        }


def _group_chunks_by_document(chunks: List[Chunk]) -> Dict[str, List[Chunk]]:
    """Group chunks by their source document URL."""
    grouped = {}
    for chunk in chunks:
        doc_url = chunk["doc_url"]
        if doc_url not in grouped:
            grouped[doc_url] = []
        grouped[doc_url].append(chunk)
    return grouped


def _deduplicate_claims(claims: List[Claim], citations: List[Citation]) -> tuple[List[Claim], List[Citation]]:
    """Remove duplicate or very similar claims."""
    # Simple deduplication based on text similarity
    unique_claims = []
    unique_citations = []
    seen_texts = set()
    
    for i, claim in enumerate(claims):
        claim_text = claim["text"].lower().strip()
        
        # Check for exact duplicates
        if claim_text in seen_texts:
            continue
        
        # Check for very similar claims (simple heuristic)
        is_duplicate = False
        for seen_text in seen_texts:
            if _texts_are_similar(claim_text, seen_text):
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_claims.append(claim)
            seen_texts.add(claim_text)
            
            # Find corresponding citation
            citation = next((c for c in citations if c["claim_id"] == claim["id"]), None)
            if citation:
                unique_citations.append(citation)
    
    return unique_claims, unique_citations


def _texts_are_similar(text1: str, text2: str, threshold: float = 0.8) -> bool:
    """Check if two texts are very similar (simple word overlap)."""
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    if not words1 or not words2:
        return False
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    similarity = len(intersection) / len(union)
    return similarity >= threshold


def _create_draft_sections(claims: List[Claim], sections: List[str], topic: str) -> List[str]:
    """Create structured draft sections from claims and suggested sections."""
    # Combine and deduplicate section suggestions
    all_sections = []
    
    # Add topic-based intro section
    all_sections.append(f"Introduction to {topic}")
    
    # Add sections from analysis
    for section in sections:
        if section and section not in all_sections:
            all_sections.append(section)
    
    # Add standard sections based on claim types
    fact_claims = [c for c in claims if c["type"] == "fact"]
    estimate_claims = [c for c in claims if c["type"] == "estimate"]
    opinion_claims = [c for c in claims if c["type"] == "opinion"]
    
    if fact_claims:
        all_sections.append("Key Facts and Findings")
    if estimate_claims:
        all_sections.append("Current Estimates and Projections")
    if opinion_claims:
        all_sections.append("Expert Opinions and Analysis")
    
    # Add conclusion
    all_sections.append("Summary and Implications")
    
    # Remove duplicates while preserving order
    unique_sections = []
    for section in all_sections:
        if section not in unique_sections:
            unique_sections.append(section)
    
    return unique_sections[:6]  # Limit to 6 sections


def _parse_json_response(content: str) -> Dict[str, Any]:
    """Parse JSON response using multiple strategies."""
    import re
    
    # Strategy 1: Try to extract and parse JSON as-is
    json_content = content.strip()
    
    # Look for JSON object boundaries if there's extra text
    if not json_content.startswith('{'):
        # Try to find JSON in the content
        json_match = re.search(r'\{.*\}', json_content, re.DOTALL)
        if json_match:
            json_content = json_match.group(0)
        else:
            raise ValueError("No JSON object found in response")
    
    # Strategy 1: Parse as-is
    try:
        return json.loads(json_content)
    except json.JSONDecodeError as e:
        logger.warning(f"Initial JSON parse failed, attempting repair: {e}")
    
    # Strategy 2: Try to repair common JSON issues
    try:
        repaired_json = _repair_json(json_content)
        return json.loads(repaired_json)
    except json.JSONDecodeError as e:
        logger.warning(f"Repaired JSON parse failed: {e}")
    
    # Strategy 3: Try to extract JSON from markdown code blocks
    try:
        code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL | re.IGNORECASE)
        if code_block_match:
            json_content = code_block_match.group(1)
            return json.loads(json_content)
        
        # Also try without code block markers
        json_match = re.search(r'\{[^}]*"claims"[^}]*\}', content, re.DOTALL)
        if json_match:
            json_content = json_match.group(0)
            return json.loads(json_content)
    except json.JSONDecodeError:
        pass
    
    # Strategy 4: Try to fix common truncation issues
    try:
        # If the JSON seems truncated, try to complete it
        if json_content.count('{') > json_content.count('}') or json_content.count('[') > json_content.count(']'):
            # Add missing closing braces and brackets
            missing_braces = json_content.count('{') - json_content.count('}')
            missing_brackets = json_content.count('[') - json_content.count(']')
            
            # Try to intelligently close the JSON structure
            completed_json = json_content
            
            # If we're in the middle of a string, close it
            if completed_json.count('"') % 2 == 1:
                completed_json += '"'
            
            # Close arrays first, then objects
            for _ in range(missing_brackets):
                completed_json += ']'
            for _ in range(missing_braces):
                completed_json += '}'
                
            return json.loads(completed_json)
    except json.JSONDecodeError:
        pass
    
    # Strategy 5: Try to create a minimal valid response if we can detect structure
    try:
        # Look for claims array structure even if malformed
        if 'claims' in content.lower():
            # Create a minimal valid structure
            minimal_json = {"claims": [], "sections": []}
            logger.warning("Created minimal JSON structure due to parsing failures")
            return minimal_json
    except Exception:
        pass
    
    # If all strategies fail, raise the original error
    raise ValueError(f"Could not parse JSON response after trying multiple strategies")


def _repair_json(json_content: str) -> str:
    """Attempt to repair common JSON formatting issues."""
    import re
    
    logger.debug(f"Attempting to repair JSON content: {json_content[:200]}...")
    
    # Clean up the content first
    json_content = json_content.strip()
    
    # Remove any text before the first {
    start_idx = json_content.find('{')
    if start_idx > 0:
        json_content = json_content[start_idx:]
    
    # Remove any text after the last }
    end_idx = json_content.rfind('}')
    if end_idx > 0 and end_idx < len(json_content) - 1:
        json_content = json_content[:end_idx + 1]
    
    # Remove any trailing commas before closing brackets/braces
    json_content = re.sub(r',\s*([}\]])', r'\1', json_content)
    
    # Fix unquoted property names (more comprehensive)
    # Handle cases like: confidence: 0.85 -> "confidence": 0.85
    json_content = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_content)
    
    # Fix missing quotes around string values that aren't already quoted
    # Handle cases like: "type": fact -> "type": "fact"
    json_content = re.sub(r':\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*([,}\]])', r': "\1"\2', json_content)
    
    # Fix missing commas between objects in arrays
    json_content = re.sub(r'}\s*{', r'}, {', json_content)
    
    # Fix missing commas between array elements
    json_content = re.sub(r']\s*\[', r'], [', json_content)
    
    # Fix missing commas between properties (handle both same-line and multiline)
    json_content = re.sub(r'"\s*\n\s*"', r'",\n"', json_content)
    json_content = re.sub(r'([0-9.}])\s*\n\s*"', r'\1,\n"', json_content)
    json_content = re.sub(r']\s*\n\s*"', r'],\n"', json_content)
    
    # Fix double quotes inside strings that break JSON
    # This is tricky - try to escape quotes that are inside string values
    def fix_quotes_in_strings(match):
        full_match = match.group(0)
        # If there are unescaped quotes inside, escape them
        if full_match.count('"') > 2:  # More than just the opening and closing quotes
            inner_content = full_match[1:-1]  # Remove outer quotes
            inner_content = inner_content.replace('"', '\\"')  # Escape inner quotes
            return f'"{inner_content}"'
        return full_match
    
    # Apply the quote fixing to string values
    json_content = re.sub(r'"[^"]*"', fix_quotes_in_strings, json_content)
    
    # Ensure the JSON ends properly
    if not json_content.rstrip().endswith('}'):
        # Count unclosed brackets and braces
        open_braces = json_content.count('{') - json_content.count('}')
        open_brackets = json_content.count('[') - json_content.count(']')
        
        # Close unclosed structures
        for _ in range(open_brackets):
            json_content += ']'
        for _ in range(open_braces):
            json_content += '}'
    
    # Final cleanup - remove any extra commas that might have been introduced
    json_content = re.sub(r',\s*([}\]])', r'\1', json_content)
    
    logger.debug(f"Repaired JSON: {json_content[:200]}...")
    return json_content


def _extract_claims_fallback(content: str, doc_urls: List[str]) -> Dict[str, Any]:
    """Fallback method to extract claims using regex when JSON parsing fails."""
    import re
    
    claims = []
    citations = []
    
    try:
        # Look for claim-like patterns in the text
        claim_pattern = r'"text":\s*"([^"]+)".*?"type":\s*"(fact|estimate|opinion)".*?"confidence":\s*([0-9.]+)'
        
        for match in re.finditer(claim_pattern, content, re.DOTALL | re.IGNORECASE):
            text = match.group(1)
            claim_type = match.group(2).lower()
            confidence = float(match.group(3))
            
            # Extract URLs mentioned near this claim
            claim_start = max(0, match.start() - 200)
            claim_end = min(len(content), match.end() + 200)
            claim_context = content[claim_start:claim_end]
            
            # Find URLs in the context
            url_pattern = r'https?://[^\s"\]]+|www\.[^\s"\]]+'
            found_urls = re.findall(url_pattern, claim_context)
            
            # Filter to only URLs from our document set
            valid_urls = [url for url in found_urls if any(doc_url in url for doc_url in doc_urls)]
            if not valid_urls:
                valid_urls = doc_urls[:1]  # Default to first document if no specific URL found
            
            claim_id = str(uuid.uuid4())[:8]
            
            claim: Claim = {
                "id": claim_id,
                "text": text,
                "type": claim_type,
                "confidence": confidence,
                "source_urls": valid_urls
            }
            claims.append(claim)
            
            citation: Citation = {
                "claim_id": claim_id,
                "urls": valid_urls,
                "citation_number": None
            }
            citations.append(citation)
            
    except Exception as e:
        logger.warning(f"Fallback extraction failed: {e}")
    
    return {
        "claims": claims,
        "citations": citations
    }