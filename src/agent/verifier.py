"""
Verifier agent module for validating claims and identifying unsupported statements.
Ensures citation coverage and triggers follow-up research for gaps.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from ..providers.cerebras_client import chat
from ..observability.logging import get_logger
from ..observability.tracing import start_span, end_span

logger = get_logger(__name__)


class Verifier:
    """Verification agent that checks claim coverage and citation quality."""
    
    def __init__(self):
        self.min_sources_per_claim = 1
        self.verification_prompt = """You are a fact-checking assistant. Review the provided claims and their sources to identify issues.

For each claim, check:
1. Is the claim supported by the provided sources?
2. Is the evidence sufficient and credible?
3. Are there any obvious gaps or contradictions?

Identify claims that need additional verification:
- Claims with no supporting sources
- Claims with weak or insufficient evidence
- Claims that contradict other information
- Claims that seem speculative or unsubstantiated

IMPORTANT: You must respond with ONLY valid JSON, no markdown, no explanations, no backticks. Start your response with {{ and end with }}.

Use this exact structure:
{{
  "verification": {{
    "verified_claims": [
      {{
        "claim": "claim text",
        "verification_status": "verified|partial|unverified",
        "source_quality": "high|medium|low",
        "notes": "verification notes"
      }}
    ],
    "unsupported_claims": ["claim 1", "claim 2"],
    "follow_up_queries": ["query 1", "query 2"],
    "coverage_assessment": {{
      "total_claims": 10,
      "verified_claims": 8,
      "partially_verified": 1,
      "unverified_claims": 1,
      "coverage_score": 0.85
    }}
  }}
}}

Claims to verify:
{claims_data}"""
    
    async def verify(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify claims coverage and identify gaps requiring follow-up.
        
        Args:
            analysis_result: Output from analyst module
        
        Returns:
            Dict containing verification results and follow-up recommendations
        """
        span_id = start_span("verify", "agent", {
            "claim_count": len(analysis_result.get("claims", []))
        })
        
        try:
            claims = analysis_result.get("claims", [])
            topic = analysis_result.get("research_topic", "")
            
            logger.info(f"Verifying {len(claims)} claims for topic: {topic}")
            
            if not claims:
                return self._empty_verification_result(topic)
            
            # Basic coverage check
            coverage_issues = self._check_basic_coverage(claims)
            
            # LLM-based verification for content quality
            llm_verification = await self._llm_verify_claims(claims, topic)
            
            # Combine results
            verified_claims = llm_verification.get("verified_claims", [])
            unsupported_claims = coverage_issues["unsupported_claims"] + llm_verification.get("unsupported_claims", [])
            
            # Remove duplicates
            unsupported_claims = list(dict.fromkeys(unsupported_claims))
            
            # Generate follow-up queries
            follow_up_queries = self._generate_follow_up_queries(
                unsupported_claims, 
                llm_verification.get("follow_up_queries", []),
                topic
            )
            
            # Calculate final coverage metrics
            total_claims = len(claims)
            verified_count = len([c for c in verified_claims if c.get("verification_status") == "verified"])
            partial_count = len([c for c in verified_claims if c.get("verification_status") == "partial"])
            unverified_count = len(unsupported_claims)
            
            coverage_score = (verified_count + 0.5 * partial_count) / max(total_claims, 1)
            
            result = {
                "research_topic": topic,
                "total_claims": total_claims,
                "verified_claims": verified_claims,
                "unsupported_claims": unsupported_claims,
                "follow_up_queries": follow_up_queries,
                "coverage_issues": coverage_issues,
                "verification_metrics": {
                    "verified_claims": verified_count,
                    "partially_verified": partial_count,
                    "unverified_claims": unverified_count,
                    "coverage_score": coverage_score,
                    "needs_follow_up": len(follow_up_queries) > 0
                },
                "success": True
            }
            
            logger.info(f"Verification completed: {verified_count}/{total_claims} verified, coverage score: {coverage_score:.2f}")
            end_span(span_id, success=True, additional_data={
                "coverage_score": coverage_score,
                "follow_up_needed": len(follow_up_queries)
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Verification failed for topic '{topic}': {e}"
            logger.error(error_msg)
            end_span(span_id, success=False, error=error_msg)
            return {
                "research_topic": analysis_result.get("research_topic", ""),
                "total_claims": len(analysis_result.get("claims", [])),
                "verified_claims": [],
                "unsupported_claims": [],
                "follow_up_queries": [],
                "coverage_issues": {},
                "verification_metrics": {
                    "verified_claims": 0,
                    "partially_verified": 0,
                    "unverified_claims": 0,
                    "coverage_score": 0,
                    "needs_follow_up": False
                },
                "success": False,
                "error": str(e)
            }
    
    def _check_basic_coverage(self, claims: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform basic coverage checks on claims.
        
        Args:
            claims: List of claims to check
        
        Returns:
            Dict with coverage issues
        """
        unsupported_claims = []
        weak_evidence_claims = []
        orphaned_claims = []
        
        for claim in claims:
            claim_text = claim.get("claim", "")
            sources = claim.get("supporting_sources", [])
            evidence_strength = claim.get("evidence_strength", "weak")
            
            # Check for unsupported claims
            if not sources or len(sources) < self.min_sources_per_claim:
                unsupported_claims.append(claim_text)
                orphaned_claims.append(claim_text)
            
            # Check for weak evidence
            elif evidence_strength == "weak":
                weak_evidence_claims.append(claim_text)
        
        return {
            "unsupported_claims": unsupported_claims,
            "weak_evidence_claims": weak_evidence_claims,
            "orphaned_claims": orphaned_claims,
            "total_issues": len(unsupported_claims) + len(weak_evidence_claims)
        }
    
    async def _llm_verify_claims(self, claims: List[Dict[str, Any]], topic: str) -> Dict[str, Any]:
        """
        Use LLM to verify claim quality and evidence.
        
        Args:
            claims: List of claims to verify
            topic: Research topic for context
        
        Returns:
            LLM verification results
        """
        try:
            # Prepare claims data for verification
            claims_data = ""
            for i, claim in enumerate(claims):
                claims_data += f"\n--- CLAIM {i+1} ---\n"
                claims_data += f"Claim: {claim.get('claim', '')}\n"
                claims_data += f"Sources: {claim.get('supporting_sources', [])}\n"
                claims_data += f"Evidence Strength: {claim.get('evidence_strength', 'unknown')}\n"
                claims_data += f"Confidence: {claim.get('confidence', 'unknown')}\n"
            
            # Create verification prompt
            prompt = self.verification_prompt.format(claims_data=claims_data)
            
            # Get verification from LLM
            messages = [
                {"role": "system", "content": f"You are verifying research claims about: {topic}"},
                {"role": "user", "content": prompt}
            ]
            
            response = chat(messages, temperature=0.1, max_tokens=1500)
            verification_text = response["content"]
            
            # Parse JSON response
            import json
            try:
                verification_data = json.loads(verification_text)
                return verification_data.get("verification", {})
            except json.JSONDecodeError:
                # Fallback parsing if JSON fails
                logger.warning("Failed to parse JSON verification, using fallback")
                return self._fallback_parse_verification(verification_text, claims)
        
        except Exception as e:
            logger.error(f"LLM verification failed: {e}")
            return {
                "verified_claims": [],
                "unsupported_claims": [],
                "follow_up_queries": []
            }
    
    def _fallback_parse_verification(self, verification_text: str, claims: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fallback parser for verification when JSON parsing fails.
        
        Args:
            verification_text: Raw verification text
            claims: Original claims
        
        Returns:
            Basic verification structure
        """
        # Simple fallback - mark claims with sources as verified
        verified_claims = []
        unsupported_claims = []
        
        for claim in claims:
            claim_text = claim.get("claim", "")
            sources = claim.get("supporting_sources", [])
            
            if sources:
                verified_claims.append({
                    "claim": claim_text,
                    "verification_status": "verified",
                    "source_quality": "medium",
                    "notes": "Fallback verification - has sources"
                })
            else:
                unsupported_claims.append(claim_text)
        
        return {
            "verified_claims": verified_claims,
            "unsupported_claims": unsupported_claims,
            "follow_up_queries": []
        }
    
    def _generate_follow_up_queries(self, unsupported_claims: List[str], 
                                   llm_queries: List[str], topic: str) -> List[str]:
        """
        Generate follow-up search queries for unsupported claims.
        
        Args:
            unsupported_claims: List of claims needing support
            llm_queries: Queries suggested by LLM
            topic: Original research topic
        
        Returns:
            List of follow-up queries
        """
        queries = []
        
        # Add LLM-suggested queries
        queries.extend(llm_queries)
        
        # Generate queries for unsupported claims
        for claim in unsupported_claims[:5]:  # Limit to 5 claims
            # Extract key terms from claim
            key_terms = self._extract_key_terms(claim)
            if key_terms:
                # Create targeted search query
                query = f"{topic} {' '.join(key_terms[:3])}"
                if query not in queries:
                    queries.append(query)
        
        # Add general follow-up queries if needed
        if len(queries) < 3:
            general_queries = [
                f"{topic} recent research",
                f"{topic} evidence studies",
                f"{topic} expert analysis"
            ]
            for query in general_queries:
                if query not in queries:
                    queries.append(query)
                    if len(queries) >= 3:
                        break
        
        return queries[:6]  # Limit total follow-up queries
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """
        Extract key terms from text for query generation.
        
        Args:
            text: Text to extract terms from
        
        Returns:
            List of key terms
        """
        import re
        
        # Simple key term extraction
        # Remove common stop words and extract meaningful terms
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
            'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 
            'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 
            'would', 'could', 'should', 'may', 'might', 'must', 'can'
        }
        
        # Extract words (alphanumeric only)
        words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9]*\b', text.lower())
        
        # Filter out stop words and short words
        key_terms = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Return unique terms, preserving order
        seen = set()
        unique_terms = []
        for term in key_terms:
            if term not in seen:
                seen.add(term)
                unique_terms.append(term)
        
        return unique_terms
    
    def _empty_verification_result(self, topic: str) -> Dict[str, Any]:
        """Return empty verification result structure."""
        return {
            "research_topic": topic,
            "total_claims": 0,
            "verified_claims": [],
            "unsupported_claims": [],
            "follow_up_queries": [],
            "coverage_issues": {
                "unsupported_claims": [],
                "weak_evidence_claims": [],
                "orphaned_claims": [],
                "total_issues": 0
            },
            "verification_metrics": {
                "verified_claims": 0,
                "partially_verified": 0,
                "unverified_claims": 0,
                "coverage_score": 0,
                "needs_follow_up": False
            },
            "success": True
        }


# Global verifier instance
verifier = Verifier()


async def verify(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for claim verification."""
    return await verifier.verify(analysis_result)