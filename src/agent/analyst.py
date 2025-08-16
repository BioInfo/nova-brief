"""
Analyst agent module for synthesizing content and tracking claim-to-source links.
Analyzes gathered information and builds structured knowledge with citations.
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from ..providers.cerebras_client import chat
from ..observability.logging import get_logger
from ..observability.tracing import start_span, end_span

logger = get_logger(__name__)


class Analyst:
    """Analysis agent that synthesizes content and tracks claims."""
    
    def __init__(self):
        self.max_chunks_per_analysis = 20
        self.analysis_prompt = """You are a research analyst. Analyze the provided content chunks and extract key findings, insights, and claims.

For each significant claim or fact you identify:
1. State the claim clearly
2. Identify which source(s) support this claim
3. Note the strength of evidence (strong, moderate, weak)
4. Identify any contradictions or gaps

IMPORTANT: You must respond with ONLY valid JSON, no markdown, no explanations, no backticks. Start your response with {{ and end with }}.

Use this exact structure:
{{
  "analysis": {{
    "main_findings": ["finding 1", "finding 2"],
    "claims": [
      {{
        "claim": "specific claim or fact",
        "supporting_sources": ["chunk_id_1", "chunk_id_2"],
        "evidence_strength": "strong|moderate|weak",
        "claim_type": "factual|opinion|statistical|definition",
        "confidence": 0.9
      }}
    ],
    "contradictions": [
      {{
        "claim_1": "first conflicting claim",
        "claim_2": "second conflicting claim",
        "sources_1": ["chunk_id"],
        "sources_2": ["chunk_id"]
      }}
    ],
    "knowledge_gaps": ["gap 1", "gap 2"],
    "summary": "brief summary of key insights"
  }}
}}

Content chunks to analyze:
{chunks_text}"""
    
    async def analyze(self, chunks: List[Dict[str, Any]], research_topic: str) -> Dict[str, Any]:
        """
        Analyze content chunks and extract structured knowledge.
        
        Args:
            chunks: List of content chunks from reader
            research_topic: Original research topic for context
        
        Returns:
            Dict containing analysis results with claims and citations
        """
        span_id = start_span("analyze", "agent", {
            "chunk_count": len(chunks),
            "topic": research_topic
        })
        
        try:
            logger.info(f"Analyzing {len(chunks)} content chunks for topic: {research_topic}")
            
            if not chunks:
                return self._empty_analysis_result(research_topic)
            
            # Process chunks in batches to stay within token limits
            all_claims = []
            all_contradictions = []
            all_findings = []
            all_gaps = []
            
            batch_size = min(self.max_chunks_per_analysis, len(chunks))
            
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i + batch_size]
                batch_analysis = await self._analyze_chunk_batch(batch_chunks, research_topic)
                
                if batch_analysis["success"]:
                    analysis_data = batch_analysis["analysis"]
                    all_claims.extend(analysis_data.get("claims", []))
                    all_contradictions.extend(analysis_data.get("contradictions", []))
                    all_findings.extend(analysis_data.get("main_findings", []))
                    all_gaps.extend(analysis_data.get("knowledge_gaps", []))
            
            # Deduplicate and consolidate results
            consolidated_claims = self._consolidate_claims(all_claims)
            unique_findings = list(dict.fromkeys(all_findings))  # Remove duplicates
            unique_gaps = list(dict.fromkeys(all_gaps))
            
            # Create claim-to-source mapping
            claim_source_map = self._build_claim_source_map(consolidated_claims)
            
            # Calculate coverage metrics
            total_chunks = len(chunks)
            cited_chunks = len(set(
                source for claim in consolidated_claims 
                for source in claim.get("supporting_sources", [])
            ))
            
            result = {
                "research_topic": research_topic,
                "total_chunks_analyzed": total_chunks,
                "claims": consolidated_claims,
                "main_findings": unique_findings,
                "contradictions": all_contradictions,
                "knowledge_gaps": unique_gaps,
                "claim_source_map": claim_source_map,
                "metrics": {
                    "total_claims": len(consolidated_claims),
                    "cited_chunks": cited_chunks,
                    "chunk_coverage": cited_chunks / max(total_chunks, 1),
                    "claims_per_chunk": len(consolidated_claims) / max(total_chunks, 1),
                    "contradictions_found": len(all_contradictions),
                    "knowledge_gaps": len(unique_gaps)
                },
                "success": True
            }
            
            logger.info(f"Analysis completed: {len(consolidated_claims)} claims extracted, {cited_chunks}/{total_chunks} chunks cited")
            end_span(span_id, success=True, additional_data={
                "total_claims": len(consolidated_claims),
                "chunk_coverage": cited_chunks / max(total_chunks, 1)
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Analysis failed for topic '{research_topic}': {e}"
            logger.error(error_msg)
            end_span(span_id, success=False, error=error_msg)
            return {
                "research_topic": research_topic,
                "total_chunks_analyzed": len(chunks),
                "claims": [],
                "main_findings": [],
                "contradictions": [],
                "knowledge_gaps": [],
                "claim_source_map": {},
                "metrics": {
                    "total_claims": 0,
                    "cited_chunks": 0,
                    "chunk_coverage": 0,
                    "claims_per_chunk": 0,
                    "contradictions_found": 0,
                    "knowledge_gaps": 0
                },
                "success": False,
                "error": str(e)
            }
    
    async def _analyze_chunk_batch(self, chunks: List[Dict[str, Any]], topic: str) -> Dict[str, Any]:
        """
        Analyze a batch of chunks using LLM.
        
        Args:
            chunks: Batch of content chunks
            topic: Research topic for context
        
        Returns:
            Analysis results for the batch
        """
        try:
            # Prepare chunks text for analysis
            chunks_text = ""
            for chunk in chunks:
                chunk_id = chunk.get("chunk_id", "unknown")
                text = chunk.get("text", "")
                title = chunk.get("document_title", "")
                url = chunk.get("document_url", "")
                
                chunks_text += f"\n--- CHUNK ID: {chunk_id} ---\n"
                chunks_text += f"Title: {title}\n"
                chunks_text += f"URL: {url}\n"
                chunks_text += f"Content: {text}\n"
            
            # Create analysis prompt
            prompt = self.analysis_prompt.format(chunks_text=chunks_text)
            
            # Get analysis from LLM
            messages = [
                {"role": "system", "content": f"You are analyzing content about: {topic}"},
                {"role": "user", "content": prompt}
            ]
            
            response = chat(messages, temperature=0.2, max_tokens=2000)
            analysis_text = response["content"]
            
            # Parse JSON response
            try:
                analysis_data = json.loads(analysis_text)
                return {
                    "analysis": analysis_data.get("analysis", {}),
                    "tokens_used": response["usage"]["total_tokens"],
                    "success": True
                }
            except json.JSONDecodeError:
                # Fallback parsing if JSON fails
                logger.warning("Failed to parse JSON analysis, using fallback")
                fallback_analysis = self._fallback_parse_analysis(analysis_text, chunks)
                return {
                    "analysis": fallback_analysis,
                    "tokens_used": response["usage"]["total_tokens"],
                    "success": True
                }
        
        except Exception as e:
            logger.error(f"Batch analysis failed: {e}")
            return {
                "analysis": {},
                "success": False,
                "error": str(e)
            }
    
    def _fallback_parse_analysis(self, analysis_text: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fallback parser for when JSON parsing fails.
        
        Args:
            analysis_text: Raw analysis text
            chunks: Original chunks for reference
        
        Returns:
            Basic analysis structure
        """
        # Extract simple findings from text
        lines = analysis_text.split('\n')
        findings = []
        claims = []
        
        chunk_ids = [chunk.get("chunk_id", f"chunk_{i}") for i, chunk in enumerate(chunks)]
        
        for line in lines:
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or '.' in line):
                cleaned_line = line.lstrip('-•').strip()
                if len(cleaned_line) > 20:  # Substantial content
                    findings.append(cleaned_line)
                    
                    # Create a basic claim from the finding
                    if len(claims) < 10:  # Limit fallback claims
                        claims.append({
                            "claim": cleaned_line,
                            "supporting_sources": chunk_ids[:2],  # Reference first chunks
                            "evidence_strength": "moderate",
                            "claim_type": "factual",
                            "confidence": 0.6
                        })
        
        return {
            "main_findings": findings[:10],  # Limit findings
            "claims": claims,
            "contradictions": [],
            "knowledge_gaps": [],
            "summary": "Analysis completed with fallback parsing"
        }
    
    def _consolidate_claims(self, claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Consolidate and deduplicate similar claims.
        
        Args:
            claims: List of claims from different batches
        
        Returns:
            Consolidated list of unique claims
        """
        if not claims:
            return []
        
        # Simple deduplication based on claim text similarity
        consolidated = []
        seen_claims = set()
        
        for claim in claims:
            claim_text = claim.get("claim", "").lower().strip()
            
            # Simple similarity check (could be enhanced with embedding similarity)
            is_duplicate = False
            for seen in seen_claims:
                if self._claims_similar(claim_text, seen):
                    is_duplicate = True
                    break
            
            if not is_duplicate and claim_text:
                seen_claims.add(claim_text)
                consolidated.append(claim)
        
        return consolidated
    
    def _claims_similar(self, claim1: str, claim2: str, threshold: float = 0.8) -> bool:
        """
        Check if two claims are similar (simple implementation).
        
        Args:
            claim1: First claim text
            claim2: Second claim text
            threshold: Similarity threshold
        
        Returns:
            True if claims are similar
        """
        # Simple word overlap similarity
        words1 = set(claim1.lower().split())
        words2 = set(claim2.lower().split())
        
        if not words1 or not words2:
            return False
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        similarity = intersection / union if union > 0 else 0
        return similarity >= threshold
    
    def _build_claim_source_map(self, claims: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Build mapping from source chunks to claims they support.
        
        Args:
            claims: List of claims with sources
        
        Returns:
            Dict mapping chunk IDs to claim texts
        """
        source_map = {}
        
        for claim in claims:
            claim_text = claim.get("claim", "")
            sources = claim.get("supporting_sources", [])
            
            for source in sources:
                if source not in source_map:
                    source_map[source] = []
                source_map[source].append(claim_text)
        
        return source_map
    
    def _empty_analysis_result(self, topic: str) -> Dict[str, Any]:
        """Return empty analysis result structure."""
        return {
            "research_topic": topic,
            "total_chunks_analyzed": 0,
            "claims": [],
            "main_findings": [],
            "contradictions": [],
            "knowledge_gaps": ["No content available for analysis"],
            "claim_source_map": {},
            "metrics": {
                "total_claims": 0,
                "cited_chunks": 0,
                "chunk_coverage": 0,
                "claims_per_chunk": 0,
                "contradictions_found": 0,
                "knowledge_gaps": 1
            },
            "success": True
        }


# Global analyst instance
analyst = Analyst()


async def analyze(chunks: List[Dict[str, Any]], research_topic: str) -> Dict[str, Any]:
    """Convenience function for content analysis."""
    return await analyst.analyze(chunks, research_topic)