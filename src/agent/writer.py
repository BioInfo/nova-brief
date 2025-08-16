"""
Writer agent module for generating final research reports with citations.
Produces structured Markdown output with numbered references and proper formatting.
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from ..providers.cerebras_client import chat
from ..observability.logging import get_logger
from ..observability.tracing import start_span, end_span

logger = get_logger(__name__)


class Writer:
    """Writing agent that generates final research reports with citations."""
    
    def __init__(self):
        self.target_word_count = 1000  # Target 800-1200 words
        self.writing_prompt = """You are a professional research writer. Create a comprehensive, well-structured research brief based on the provided analysis.

Requirements:
- 800-1200 words in professional, analytical tone
- Clear structure with meaningful headings
- Every significant claim must cite sources using [1], [2], etc.
- Include brief introduction and conclusion
- Use markdown formatting
- Focus on key insights and findings
- Maintain objectivity and analytical perspective

Structure your brief as:
1. Executive Summary (2-3 sentences)
2. Key Findings (main insights with citations)
3. Detailed Analysis (supporting evidence and context)
4. Implications and Considerations
5. Conclusion

Research Topic: {topic}

Verified Claims with Sources:
{claims_data}

Additional Context:
{context_data}

Write a comprehensive research brief with proper citations. Use numbered citations [1], [2], etc. that correspond to the source list that will be appended."""
    
    async def write(self, verification_result: Dict[str, Any], 
                   analysis_result: Dict[str, Any], 
                   documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate final research report with citations.
        
        Args:
            verification_result: Output from verifier module
            analysis_result: Output from analyst module  
            documents: Source documents from reader
        
        Returns:
            Dict containing formatted report and metadata
        """
        span_id = start_span("write", "agent", {
            "topic": verification_result.get("research_topic", "")
        })
        
        try:
            topic = verification_result.get("research_topic", "Unknown Topic")
            
            logger.info(f"Writing research brief for topic: {topic}")
            
            # Prepare content for writing
            verified_claims = verification_result.get("verified_claims", [])
            all_claims = analysis_result.get("claims", [])
            findings = analysis_result.get("main_findings", [])
            
            # Create source mapping and reference list
            source_mapping, reference_list = self._create_source_mapping(all_claims, documents)
            
            # Generate main content using LLM
            main_content = await self._generate_content(
                topic, verified_claims, findings, source_mapping
            )
            
            # Format final report
            formatted_report = self._format_final_report(
                topic, main_content, reference_list, verification_result, analysis_result
            )
            
            # Calculate metrics
            word_count = len(formatted_report.split())
            citation_count = len(re.findall(r'\[\d+\]', formatted_report))
            
            result = {
                "research_topic": topic,
                "report_markdown": formatted_report,
                "reference_list": reference_list,
                "source_mapping": source_mapping,
                "metrics": {
                    "word_count": word_count,
                    "citation_count": citation_count,
                    "reference_count": len(reference_list),
                    "claims_cited": len([c for c in all_claims if c.get("supporting_sources")]),
                    "total_claims": len(all_claims),
                    "coverage_score": verification_result.get("verification_metrics", {}).get("coverage_score", 0)
                },
                "generation_metadata": {
                    "verified_claims": len(verified_claims),
                    "total_findings": len(findings),
                    "source_documents": len(documents)
                },
                "success": True
            }
            
            logger.info(f"Research brief completed: {word_count} words, {citation_count} citations, {len(reference_list)} references")
            end_span(span_id, success=True, additional_data={
                "word_count": word_count,
                "citation_count": citation_count
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Writing failed for topic '{topic}': {e}"
            logger.error(error_msg)
            end_span(span_id, success=False, error=error_msg)
            return {
                "research_topic": verification_result.get("research_topic", ""),
                "report_markdown": "",
                "reference_list": [],
                "source_mapping": {},
                "metrics": {
                    "word_count": 0,
                    "citation_count": 0,
                    "reference_count": 0,
                    "claims_cited": 0,
                    "total_claims": 0,
                    "coverage_score": 0
                },
                "generation_metadata": {},
                "success": False,
                "error": str(e)
            }
    
    def _create_source_mapping(self, claims: List[Dict[str, Any]], 
                              documents: List[Dict[str, Any]]) -> Tuple[Dict[str, int], List[Dict[str, Any]]]:
        """
        Create mapping from source chunks to citation numbers and reference list.
        
        Args:
            claims: List of claims with source references
            documents: List of source documents
        
        Returns:
            Tuple of (source_mapping, reference_list)
        """
        # Extract all source chunk IDs from claims
        all_source_ids = set()
        for claim in claims:
            for source_id in claim.get("supporting_sources", []):
                all_source_ids.add(source_id)
        
        # Create document URL to info mapping
        doc_map = {doc["url"]: doc for doc in documents}
        
        # Build reference list and mapping
        reference_list = []
        source_mapping = {}
        ref_number = 1
        
        for source_id in sorted(all_source_ids):
            # Extract URL from chunk ID (format: url#chunk_number)
            if '#' in source_id:
                url = source_id.split('#')[0]
            else:
                url = source_id
            
            # Skip if we already have this URL
            if url in [ref.get("url") for ref in reference_list]:
                # Find existing reference number
                for i, ref in enumerate(reference_list):
                    if ref.get("url") == url:
                        source_mapping[source_id] = i + 1
                        break
                continue
            
            # Get document info
            doc_info = doc_map.get(url, {})
            
            reference = {
                "number": ref_number,
                "title": doc_info.get("title", "Unknown Title"),
                "url": url,
                "domain": doc_info.get("domain", ""),
                "access_date": "2024"  # Could be made dynamic
            }
            
            reference_list.append(reference)
            source_mapping[source_id] = ref_number
            
            # Map all chunk IDs from this URL to same reference number
            for other_source_id in all_source_ids:
                if other_source_id.startswith(url):
                    source_mapping[other_source_id] = ref_number
            
            ref_number += 1
        
        return source_mapping, reference_list
    
    async def _generate_content(self, topic: str, verified_claims: List[Dict[str, Any]], 
                               findings: List[str], source_mapping: Dict[str, int]) -> str:
        """
        Generate main content using LLM.
        
        Args:
            topic: Research topic
            verified_claims: List of verified claims
            findings: List of key findings
            source_mapping: Mapping from sources to citation numbers
        
        Returns:
            Generated content text
        """
        try:
            # Prepare claims data with citation numbers
            claims_data = ""
            for i, claim in enumerate(verified_claims):
                claim_text = claim.get("claim", "")
                sources = claim.get("supporting_sources", [])
                
                # Map sources to citation numbers
                citations = []
                for source in sources:
                    if source in source_mapping:
                        citations.append(f"[{source_mapping[source]}]")
                
                claims_data += f"\n{i+1}. {claim_text}"
                if citations:
                    claims_data += f" {' '.join(citations)}"
                claims_data += "\n"
            
            # Prepare context data
            context_data = "\n".join([f"- {finding}" for finding in findings[:10]])
            
            # Create writing prompt
            prompt = self.writing_prompt.format(
                topic=topic,
                claims_data=claims_data,
                context_data=context_data
            )
            
            # Generate content
            messages = [
                {"role": "system", "content": "You are a professional research writer creating analytical briefs."},
                {"role": "user", "content": prompt}
            ]
            
            response = chat(messages, temperature=0.3, max_tokens=2500)
            return response["content"]
        
        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            return self._fallback_content(topic, verified_claims, findings)
    
    def _fallback_content(self, topic: str, claims: List[Dict[str, Any]], findings: List[str]) -> str:
        """
        Generate fallback content when LLM generation fails.
        
        Args:
            topic: Research topic
            claims: List of claims
            findings: List of findings
        
        Returns:
            Basic structured content
        """
        content = f"# Research Brief: {topic}\n\n"
        content += "## Executive Summary\n\n"
        content += f"This brief examines {topic} based on available research and sources.\n\n"
        
        content += "## Key Findings\n\n"
        for i, finding in enumerate(findings[:5], 1):
            content += f"{i}. {finding}\n"
        
        content += "\n## Analysis\n\n"
        content += f"Research on {topic} reveals several important aspects:\n\n"
        
        for claim in claims[:3]:
            claim_text = claim.get("claim", "")
            if claim_text:
                content += f"- {claim_text}\n"
        
        content += "\n## Conclusion\n\n"
        content += f"Based on the available evidence, {topic} presents both opportunities and challenges that warrant further investigation.\n"
        
        return content
    
    def _format_final_report(self, topic: str, main_content: str, reference_list: List[Dict[str, Any]], 
                            verification_result: Dict[str, Any], analysis_result: Dict[str, Any]) -> str:
        """
        Format the final report with metadata and references.
        
        Args:
            topic: Research topic
            main_content: Generated main content
            reference_list: List of references
            verification_result: Verification results
            analysis_result: Analysis results
        
        Returns:
            Complete formatted report
        """
        # Start with main content
        report = main_content
        
        # Ensure proper title
        if not report.startswith("#"):
            report = f"# Research Brief: {topic}\n\n" + report
        
        # Add references section
        if reference_list:
            report += "\n\n## References\n\n"
            for ref in reference_list:
                title = ref.get("title", "Unknown Title")
                url = ref.get("url", "")
                domain = ref.get("domain", "")
                
                # Format reference
                ref_line = f"{ref['number']}. {title}"
                if domain:
                    ref_line += f" - {domain}"
                if url:
                    ref_line += f" [{url}]({url})"
                
                report += ref_line + "\n"
        
        # Add research metadata (optional footer)
        coverage_score = verification_result.get("verification_metrics", {}).get("coverage_score", 0)
        total_claims = verification_result.get("total_claims", 0)
        
        report += f"\n---\n\n"
        report += f"*Research completed with {len(reference_list)} sources. "
        report += f"Coverage score: {coverage_score:.1%} ({total_claims} claims analyzed).*\n"
        
        return report
    
    def _clean_markdown(self, text: str) -> str:
        """
        Clean and validate markdown formatting.
        
        Args:
            text: Raw markdown text
        
        Returns:
            Cleaned markdown
        """
        # Basic markdown cleaning
        # Fix multiple line breaks
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Ensure proper heading spacing
        text = re.sub(r'(^|\n)(#{1,6})', r'\1\n\2', text)
        text = re.sub(r'(#{1,6}[^\n]*)\n{0,1}([^#\n])', r'\1\n\n\2', text)
        
        # Clean up citation formatting
        text = re.sub(r'\[\s*(\d+)\s*\]', r'[\1]', text)
        
        return text.strip()


# Global writer instance
writer = Writer()


async def write(verification_result: Dict[str, Any], 
               analysis_result: Dict[str, Any], 
               documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convenience function for report writing."""
    return await writer.write(verification_result, analysis_result, documents)