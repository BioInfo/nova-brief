"""Writer component for generating final research reports with citations."""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from ..providers.openrouter_client import chat, create_json_schema_format
from ..storage.models import Claim, Citation, Reference, Report
from ..observability.logging import get_logger
from ..observability.tracing import TimedOperation, emit_event

logger = get_logger(__name__)


WRITING_SYSTEM_PROMPT = """You are an expert research writer who creates comprehensive, well-structured reports. Your task is to:

1. Transform research claims into a coherent, analytical narrative
2. Organize content into logical sections with clear flow
3. Include proper in-text citations using numbered format [1], [2], etc.
4. Write in an authoritative, analytical tone suitable for professional briefings
5. Ensure coverage of all major findings while maintaining readability
6. Target 800-1200 words for comprehensive coverage

Guidelines:
- Start with a concise introduction that establishes context
- Organize findings into themed sections based on the research
- Use numbered citations [1] immediately after claims requiring sources
- Include quantitative data and specific examples where available
- Address multiple perspectives when relevant
- Conclude with key implications and future considerations
- Maintain objective, professional tone throughout

YOU MUST respond with ONLY a valid JSON object in this exact format:
{
  "report_markdown": "Complete markdown report with numbered citations",
  "key_findings": ["finding 1", "finding 2", "finding 3"],
  "executive_summary": "Brief executive summary (2-3 sentences)"
}

DO NOT include any text before or after the JSON. ONLY return the JSON object."""


async def write(
    claims: List[Claim],
    citations: List[Citation],
    draft_sections: List[str],
    topic: str,
    sub_questions: List[str],
    coverage_report: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate final research report with citations and references.
    
    Args:
        claims: Verified claims to include in report
        citations: Citation information for sources
        draft_sections: Suggested section structure
        topic: Main research topic
        sub_questions: Research questions addressed
        coverage_report: Verification coverage metrics
    
    Returns:
        Dictionary with success status, report, and metadata
    """
    with TimedOperation("agent_writer") as timer:
        try:
            if not claims:
                return {
                    "success": False,
                    "error": "No claims provided for report generation",
                    "report_md": "",
                    "references": []
                }
            
            logger.info(f"Writing report for '{topic}' with {len(claims)} claims")
            
            # Organize claims by type and confidence
            organized_claims = _organize_claims_for_writing(claims)
            
            # Create citation mapping and assign numbers
            citation_map, references = _create_citation_mapping(citations)
            
            # Generate report content using LLM
            report_content = await _generate_report_content(
                topic,
                sub_questions,
                organized_claims,
                citation_map,
                draft_sections
            )
            
            if not report_content["success"]:
                logger.error(f"Report generation failed: {report_content.get('error')}")
                return {
                    "success": False,
                    "error": f"Content generation failed: {report_content.get('error')}",
                    "report_md": "",
                    "references": []
                }
            
            # Extract and format the report
            report_md = report_content["report_markdown"]
            
            # Add references section
            report_md = _add_references_section(report_md, references)
            
            # Validate and clean up formatting
            report_md = _clean_report_formatting(report_md)
            
            # Calculate report metrics
            word_count = len(report_md.split())
            citation_count = len(references)
            
            # Create structured report object
            report_metadata = {
                "topic": topic,
                "word_count": word_count,
                "citation_count": citation_count,
                "claims_included": len(claims),
                "sections": _extract_section_headers(report_md),
                "created_at": datetime.now().isoformat(),
                "coverage_metrics": coverage_report or {},
                "sub_questions_addressed": len(sub_questions)
            }
            
            report: Report = {
                "topic": topic,
                "report_md": report_md,
                "references": references,
                "metadata": report_metadata,
                "sections": _extract_section_headers(report_md),
                "word_count": word_count,
                "created_at": datetime.now().isoformat()
            }
            
            logger.info(
                f"Report completed: {word_count} words, {citation_count} references",
                extra=report_metadata
            )
            
            emit_event(
                "report_generated",
                metadata=report_metadata
            )
            
            return {
                "success": True,
                "report": report,
                "report_md": report_md,
                "references": references,
                "metadata": report_metadata
            }
            
        except Exception as e:
            logger.error(f"Report writing failed: {e}")
            emit_event(
                "writing_error",
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
                "report_md": "",
                "references": []
            }


async def _generate_report_content(
    topic: str,
    sub_questions: List[str],
    organized_claims: Dict[str, List[Claim]],
    citation_map: Dict[str, int],
    draft_sections: List[str]
) -> Dict[str, Any]:
    """Generate report content using LLM with structured output."""
    
    try:
        # Prepare content for LLM
        content_summary = _prepare_content_summary(organized_claims, citation_map)
        
        # Create user prompt
        user_prompt = f"""Research Topic: {topic}

Research Questions Addressed:
{chr(10).join(f"- {q}" for q in sub_questions)}

Suggested Section Structure:
{chr(10).join(f"- {s}" for s in draft_sections)}

Research Findings and Claims:
{content_summary}

Citation Format: Use [1], [2], etc. for in-text citations matching the claim sources.

Generate a comprehensive research report in markdown format. Include:
1. Introduction establishing context
2. Main findings organized by themes
3. Proper numbered citations [1], [2], etc.
4. Conclusion with implications
Target: 800-1200 words."""

        # Define JSON schema for structured report output
        json_schema = {
            "type": "object",
            "properties": {
                "report_markdown": {
                    "type": "string",
                    "description": "Complete markdown report with numbered citations"
                },
                "key_findings": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of key findings from the research"
                },
                "executive_summary": {
                    "type": "string",
                    "description": "Brief executive summary (2-3 sentences)"
                }
            },
            "required": ["report_markdown", "key_findings", "executive_summary"],
            "additionalProperties": False
        }
        
        # Call LLM for report generation (using prompt-based JSON instead of structured output)
        messages = [
            {"role": "system", "content": WRITING_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]
        
        response = await chat(
            messages=messages,
            temperature=0.2,
            max_tokens=3000
            # Note: Removed response_format as it doesn't work with gpt-oss-120b
        )
        
        if not response["success"]:
            return {
                "success": False,
                "error": f"LLM call failed: {response.get('error')}",
                "report_markdown": ""
            }
        
        # Parse response with robust JSON extraction and debugging
        try:
            content = response.get("content", "")
            
            # Enhanced debugging for empty responses
            if not content:
                logger.error("Empty response content detected")
                logger.error(f"Full response object: {response}")
                logger.error(f"Response keys: {list(response.keys())}")
                
                # Check if there's any other content in the response
                if "response" in response:
                    resp_obj = response["response"]
                    logger.error(f"Response object type: {type(resp_obj)}")
                    if hasattr(resp_obj, 'choices') and resp_obj.choices:
                        choice = resp_obj.choices[0]
                        logger.error(f"Choice object: {choice}")
                        logger.error(f"Choice message: {choice.message}")
                        logger.error(f"Choice finish_reason: {getattr(choice, 'finish_reason', 'N/A')}")
                
                # Try one more retry with a simpler prompt
                logger.info("Attempting retry with simplified prompt")
                return await _retry_with_simple_prompt(
                    topic, sub_questions, organized_claims, citation_map
                )
            
            # Enhanced content debugging
            logger.debug(f"Raw content length: {len(content)}")
            logger.debug(f"Content preview: {content[:200]}...")
            
            # Try direct JSON parsing first
            try:
                result = json.loads(content)
                logger.debug("Direct JSON parsing successful")
            except json.JSONDecodeError as json_err:
                logger.warning(f"Direct JSON parsing failed: {json_err}")
                # Fallback: Extract JSON from text using regex
                import re
                
                # Try multiple JSON extraction patterns
                json_patterns = [
                    r'\{.*\}',  # Original pattern
                    r'```json\s*(\{.*?\})\s*```',  # JSON in code blocks
                    r'```\s*(\{.*?\})\s*```',  # Generic code blocks
                    r'(\{[^{}]*"report_markdown"[^{}]*\})'  # Target specific JSON
                ]
                
                result = None
                for pattern in json_patterns:
                    json_match = re.search(pattern, content, re.DOTALL)
                    if json_match:
                        try:
                            json_content = json_match.group(1) if len(json_match.groups()) > 0 else json_match.group(0)
                            result = json.loads(json_content)
                            logger.info(f"JSON extracted successfully with pattern: {pattern}")
                            break
                        except json.JSONDecodeError:
                            continue
                
                if not result:
                    logger.error("All JSON extraction patterns failed")
                    raise ValueError("No valid JSON found in response")
            
            report_markdown = result.get("report_markdown", "")
            
            if not report_markdown:
                logger.warning("No report_markdown field found in JSON response")
                # Try to find content in other fields
                for field in ["content", "report", "markdown", "text"]:
                    if field in result and result[field]:
                        report_markdown = result[field]
                        logger.info(f"Using content from field: {field}")
                        break
                
                if not report_markdown:
                    raise ValueError("No report content found in any expected fields")
            
            return {
                "success": True,
                "report_markdown": report_markdown,
                "key_findings": result.get("key_findings", []),
                "executive_summary": result.get("executive_summary", "")
            }
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse report response: {e}")
            logger.error(f"Raw content ({len(content)} chars): {content}")
            
            # Enhanced fallback: try to extract content directly
            raw_content = response.get("content", "")
            if raw_content and len(raw_content) > 100:
                # Check if it looks like markdown content
                if any(marker in raw_content.lower() for marker in ["#", "##", "introduction", "conclusion"]):
                    logger.info("Using raw content as fallback markdown")
                    return {
                        "success": True,
                        "report_markdown": raw_content,
                        "key_findings": [],
                        "executive_summary": "Report generated using fallback content extraction."
                    }
            
            # Final fallback: try simple prompt
            logger.info("Attempting final retry with basic prompt")
            return await _retry_with_simple_prompt(
                topic, sub_questions, organized_claims, citation_map
            )
        
    except Exception as e:
        logger.error(f"Content generation failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "report_markdown": ""
        }


async def _retry_with_simple_prompt(
    topic: str,
    sub_questions: List[str],
    organized_claims: Dict[str, List[Claim]],
    citation_map: Dict[str, int]
) -> Dict[str, Any]:
    """
    Retry report generation with a simplified prompt when structured output fails.
    """
    try:
        logger.info("Attempting simple prompt retry for report generation")
        
        # Create a very simple prompt that doesn't require JSON
        simple_prompt = f"""Write a comprehensive research report on: {topic}

Research Questions:
{chr(10).join(f"- {q}" for q in sub_questions)}

Key Findings:
{_prepare_simple_content_summary(organized_claims, citation_map)}

Instructions:
- Write in markdown format
- Include an introduction, main findings, and conclusion
- Use numbered citations [1], [2], etc.
- Target 800-1200 words
- Write in professional, analytical tone

Please write the complete report now:"""

        # Use a simple system prompt
        simple_system = "You are a professional research writer. Write clear, well-structured reports based on the provided research findings."
        
        messages = [
            {"role": "system", "content": simple_system},
            {"role": "user", "content": simple_prompt}
        ]
        
        response = await chat(
            messages=messages,
            temperature=0.3,
            max_tokens=3000
        )
        
        if not response["success"]:
            return {
                "success": False,
                "error": f"Simple prompt retry failed: {response.get('error')}",
                "report_markdown": ""
            }
        
        content = response.get("content", "")
        if not content:
            return {
                "success": False,
                "error": "Simple prompt retry returned empty content",
                "report_markdown": ""
            }
        
        # Clean up the content and ensure it's reasonable
        if len(content) < 200:
            return {
                "success": False,
                "error": "Simple prompt retry returned insufficient content",
                "report_markdown": ""
            }
        
        logger.info(f"Simple prompt retry successful: {len(content)} characters generated")
        
        return {
            "success": True,
            "report_markdown": content,
            "key_findings": [],
            "executive_summary": f"Research report on {topic} generated using simplified prompt."
        }
        
    except Exception as e:
        logger.error(f"Simple prompt retry failed: {e}")
        return {
            "success": False,
            "error": f"Simple prompt retry exception: {str(e)}",
            "report_markdown": ""
        }


def _prepare_simple_content_summary(
    organized_claims: Dict[str, List[Claim]],
    citation_map: Dict[str, int]
) -> str:
    """Prepare a simplified content summary for retry attempts."""
    content_parts = []

    for category, claims in organized_claims.items():
        if not claims:
            continue
            
        # Limit to top claims to avoid overwhelming the prompt
        top_claims = claims[:5] if len(claims) > 5 else claims
        
        for claim in top_claims:
            # Find citation numbers for this claim
            citation_numbers = []
            for url in claim["source_urls"]:
                if url in citation_map:
                    citation_numbers.append(str(citation_map[url]))
            
            citation_str = f"[{', '.join(citation_numbers)}]" if citation_numbers else ""
            content_parts.append(f"- {claim['text']} {citation_str}")

    return "\n".join(content_parts)


def _organize_claims_for_writing(claims: List[Claim]) -> Dict[str, List[Claim]]:
    """Organize claims by type and confidence for structured writing."""
    organized = {
        "high_confidence_facts": [],
        "medium_confidence_facts": [],
        "estimates_and_projections": [],
        "expert_opinions": [],
        "other_findings": []
    }
    
    for claim in claims:
        if claim["type"] == "fact":
            if claim["confidence"] >= 0.8:
                organized["high_confidence_facts"].append(claim)
            else:
                organized["medium_confidence_facts"].append(claim)
        elif claim["type"] == "estimate":
            organized["estimates_and_projections"].append(claim)
        elif claim["type"] == "opinion":
            organized["expert_opinions"].append(claim)
        else:
            organized["other_findings"].append(claim)
    
    return organized


def _create_citation_mapping(citations: List[Citation]) -> tuple[Dict[str, int], List[Reference]]:
    """Create citation number mapping and reference list."""
    citation_map = {}
    references = []
    citation_number = 1
    
    # Track URLs to avoid duplicates in references
    seen_urls = set()
    
    for citation in citations:
        for url in citation["urls"]:
            if url not in seen_urls:
                citation_map[url] = citation_number
                
                # Create reference entry
                reference: Reference = {
                    "number": citation_number,
                    "url": url,
                    "title": _extract_title_from_url(url),
                    "access_date": datetime.now().strftime("%Y-%m-%d")
                }
                references.append(reference)
                
                seen_urls.add(url)
                citation_number += 1
    
    return citation_map, references


def _prepare_content_summary(
    organized_claims: Dict[str, List[Claim]],
    citation_map: Dict[str, int]
) -> str:
    """Prepare organized content summary for LLM."""
    content_parts = []
    
    for category, claims in organized_claims.items():
        if not claims:
            continue
            
        content_parts.append(f"\n{category.replace('_', ' ').title()}:")
        
        for claim in claims:
            # Find citation numbers for this claim
            citation_numbers = []
            for url in claim["source_urls"]:
                if url in citation_map:
                    citation_numbers.append(str(citation_map[url]))
            
            citation_str = f"[{', '.join(citation_numbers)}]" if citation_numbers else "[?]"
            
            content_parts.append(f"- {claim['text']} {citation_str}")
    
    return "\n".join(content_parts)


def _add_references_section(report_md: str, references: List[Reference]) -> str:
    """Add references section to the report."""
    if not references:
        return report_md
    
    references_section = "\n\n## References\n\n"
    
    for ref in sorted(references, key=lambda x: x["number"]):
        references_section += f"{ref['number']}. {ref['url']}"
        if ref.get("title"):
            references_section += f" - {ref['title']}"
        if ref.get("access_date"):
            references_section += f" (Accessed: {ref['access_date']})"
        references_section += "\n"
    
    return report_md + references_section


def _clean_report_formatting(report_md: str) -> str:
    """Clean and validate report formatting."""
    # Remove extra whitespace
    lines = [line.strip() for line in report_md.split('\n')]
    
    # Remove empty lines at start and end
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    
    # Ensure proper spacing around headers
    cleaned_lines = []
    for i, line in enumerate(lines):
        if line.startswith('#'):
            # Add blank line before headers (except first)
            if i > 0 and lines[i-1]:
                cleaned_lines.append('')
            cleaned_lines.append(line)
            # Add blank line after headers if next line isn't blank
            if i < len(lines) - 1 and lines[i+1]:
                cleaned_lines.append('')
        else:
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines)


def _extract_section_headers(report_md: str) -> List[str]:
    """Extract section headers from markdown report."""
    headers = []
    for line in report_md.split('\n'):
        line = line.strip()
        if line.startswith('#'):
            # Remove markdown header syntax and clean
            header = line.lstrip('#').strip()
            if header:
                headers.append(header)
    return headers


def _extract_title_from_url(url: str) -> Optional[str]:
    """Extract a simple title from URL for reference formatting."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc
        path = parsed.path
        
        # Simple title extraction
        if path and path != '/':
            title_parts = path.split('/')[-1].split('-')
            if title_parts:
                return ' '.join(word.capitalize() for word in title_parts[:3])
        
        return domain
    except Exception:
        return None


# Utility functions for report processing
def validate_report_structure(report_md: str) -> Dict[str, Any]:
    """Validate report structure and content."""
    validation = {
        "has_introduction": False,
        "has_conclusion": False,
        "has_citations": False,
        "has_references": False,
        "word_count": 0,
        "section_count": 0,
        "citation_count": 0
    }
    
    lines = report_md.split('\n')
    validation["word_count"] = len(report_md.split())
    
    # Check for structural elements
    content_lower = report_md.lower()
    validation["has_introduction"] = any(word in content_lower for word in ["introduction", "overview", "background"])
    validation["has_conclusion"] = any(word in content_lower for word in ["conclusion", "summary", "implications"])
    validation["has_references"] = "## references" in content_lower or "# references" in content_lower
    
    # Count sections and citations
    validation["section_count"] = len([line for line in lines if line.strip().startswith('#')])
    
    import re
    citations = re.findall(r'\[\d+\]', report_md)
    validation["citation_count"] = len(set(citations))
    validation["has_citations"] = validation["citation_count"] > 0
    
    return validation


def export_report_to_json(report: Report) -> str:
    """Export report to JSON format for API/storage."""
    return json.dumps(report, indent=2, default=str)