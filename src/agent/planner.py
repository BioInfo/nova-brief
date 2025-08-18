"""Planner component for transforming topics into search queries."""

import uuid
from typing import Dict, List, Any
from ..providers.openrouter_client import LLMClient
from ..storage.models import Constraints
from ..config import Config
from ..observability.logging import get_logger
from ..observability.tracing import TimedOperation, emit_event

logger = get_logger(__name__)


PLANNING_SYSTEM_PROMPT = """You are a research planning expert. Your task is to break down research topics into focused sub-questions and generate diverse search queries that will help find credible, authoritative sources.

Guidelines:
1. Generate 3-5 specific sub-questions that comprehensively cover the topic
2. Create 5-8 diverse search queries using different approaches:
   - Direct topic searches
   - Question-based searches
   - Specific aspect searches
   - Authority/expert searches (site:edu, site:gov)
   - Recent news/analysis searches
3. Vary search operators and synonyms
4. Focus on finding authoritative, credible sources
5. Avoid duplicate or overly similar queries

YOU MUST respond with ONLY a valid JSON object in this exact format:
{
  "sub_questions": ["question1", "question2", ...],
  "queries": ["query1", "query2", ...]
}

DO NOT include any text before or after the JSON. ONLY return the JSON object."""


REFINEMENT_SYSTEM_PROMPT = """You are a research planning expert specializing in adaptive research refinement. Your task is to analyze initial research results and identify gaps, then generate additional targeted sub-questions and search queries to fill those gaps.

Guidelines:
1. Analyze what information has been found vs. what was originally sought
2. Identify specific knowledge gaps, missing perspectives, or incomplete coverage
3. Generate 2-4 new targeted sub-questions that address the identified gaps
4. Create 3-6 new search queries that specifically target the missing information
5. Focus on filling gaps rather than duplicating existing coverage
6. Consider different angles, timeframes, or expert perspectives not yet covered
7. Prioritize queries most likely to find authoritative, missing information

YOU MUST respond with ONLY a valid JSON object in this exact format:
{
  "gaps_identified": ["gap1", "gap2", ...],
  "new_sub_questions": ["question1", "question2", ...],
  "new_queries": ["query1", "query2", ...],
  "refinement_rationale": "Brief explanation of why these additions are needed"
}

DO NOT include any text before or after the JSON. ONLY return the JSON object."""


async def plan(
    topic: str,
    constraints: Constraints
) -> Dict[str, Any]:
    """
    Generate sub-questions and search queries for a research topic.
    
    Args:
        topic: Research topic to plan for
        constraints: Research constraints including domain filters
    
    Returns:
        Dictionary with success status, sub-questions, and queries
    """
    with TimedOperation("agent_planner") as timer:
        try:
            if not topic or not topic.strip():
                return {
                    "success": False,
                    "error": "INVALID_TOPIC",
                    "sub_questions": [],
                    "queries": []
                }
            
            logger.info(f"Planning research for topic: {topic}")
            
            # Prepare planning prompt
            user_prompt = f"Research topic: {topic}\n\n"
            
            # Add domain constraints to prompt
            if constraints.get("include_domains"):
                user_prompt += f"Focus on these domains: {', '.join(constraints['include_domains'])}\n"
            if constraints.get("exclude_domains"):
                user_prompt += f"Avoid these domains: {', '.join(constraints['exclude_domains'])}\n"
            if constraints.get("date_range"):
                user_prompt += f"Time focus: {constraints['date_range']}\n"
            
            user_prompt += "\nGenerate sub-questions and diverse search queries for comprehensive research."
            
            # Get selected model
            selected_model = Config.SELECTED_MODEL
            
            # Initialize LLM client with selected model
            client = LLMClient(model_key=selected_model)
            
            # Call LLM for planning
            messages = [
                {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await client.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=1000
                # Note: Removed response_format as it doesn't work with all models
            )
            
            if not response["success"]:
                logger.error(f"LLM call failed: {response.get('error')}")
                return {
                    "success": False,
                    "error": f"LLM_ERROR: {response.get('error')}",
                    "sub_questions": [],
                    "queries": []
                }
            
            # Parse response content with robust JSON extraction
            try:
                import json
                content = response.get("content", "")
                if not content:
                    raise ValueError("Empty response content")
                
                # Try direct JSON parsing first
                try:
                    planning_result = json.loads(content)
                except json.JSONDecodeError:
                    # Fallback: Extract JSON from text using regex
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        planning_result = json.loads(json_match.group(0))
                    else:
                        raise ValueError("No valid JSON found in response")
                
                sub_questions = planning_result.get("sub_questions", [])
                queries = planning_result.get("queries", [])
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse planning response: {e}")
                logger.error(f"Raw content: {content[:500]}...")
                # Fallback to simple queries
                sub_questions, queries = _generate_fallback_plan(topic, constraints)
            
            # Validate and clean results
            sub_questions = [q.strip() for q in sub_questions if q.strip()]
            queries = [q.strip() for q in queries if q.strip()]
            
            # Apply domain filters to queries
            if constraints.get("include_domains") or constraints.get("exclude_domains"):
                queries = _apply_domain_filters_to_queries(queries, constraints)
            
            # Ensure minimum requirements
            if len(queries) < 3:
                fallback_sub, fallback_queries = _generate_fallback_plan(topic, constraints)
                sub_questions.extend(fallback_sub)
                queries.extend(fallback_queries)
            
            # Deduplicate
            sub_questions = list(dict.fromkeys(sub_questions))[:5]
            queries = list(dict.fromkeys(queries))[:8]
            
            logger.info(
                f"Planning completed: {len(sub_questions)} sub-questions, {len(queries)} queries",
                extra={
                    "topic": topic,
                    "sub_questions_count": len(sub_questions),
                    "queries_count": len(queries)
                }
            )
            
            emit_event(
                "planning_completed",
                metadata={
                    "topic": topic,
                    "sub_questions_count": len(sub_questions),
                    "queries_count": len(queries),
                    "has_domain_constraints": bool(constraints.get("include_domains") or constraints.get("exclude_domains"))
                }
            )
            
            return {
                "success": True,
                "sub_questions": sub_questions,
                "queries": queries,
                "metadata": {
                    "topic": topic,
                    "planning_method": "llm_structured"
                }
            }
            
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            
            # Fallback planning
            try:
                sub_questions, queries = _generate_fallback_plan(topic, constraints)
                logger.info("Using fallback planning")
                
                return {
                    "success": True,
                    "sub_questions": sub_questions,
                    "queries": queries,
                    "metadata": {
                        "topic": topic,
                        "planning_method": "fallback",
                        "original_error": str(e)
                    }
                }
            except Exception as fallback_error:
                logger.error(f"Fallback planning also failed: {fallback_error}")
                return {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "sub_questions": [],
                    "queries": []
                }


async def refine_plan(
    original_topic: str,
    original_sub_questions: List[str],
    original_queries: List[str],
    claims_found: List[Dict[str, Any]],
    search_results: List[Dict[str, Any]],
    constraints: Constraints
) -> Dict[str, Any]:
    """
    Refine the research plan based on initial results to identify and fill gaps.
    
    Args:
        original_topic: The original research topic
        original_sub_questions: Initially planned sub-questions
        original_queries: Initially planned search queries
        claims_found: Claims extracted from initial research
        search_results: Search results from initial queries
        constraints: Research constraints
    
    Returns:
        Dictionary with refinement results including new questions and queries
    """
    with TimedOperation("agent_planner_refinement") as timer:
        try:
            logger.info(f"Refining research plan for topic: {original_topic}")
            
            # Analyze coverage and identify gaps
            coverage_analysis = _analyze_coverage(
                original_sub_questions,
                claims_found,
                search_results
            )
            
            # Prepare refinement prompt
            user_prompt = f"""Original Research Topic: {original_topic}

Original Sub-Questions:
{chr(10).join(f"- {q}" for q in original_sub_questions)}

Claims Found So Far:
{chr(10).join(f"- {claim.get('text', '')[:100]}..." for claim in claims_found[:8])}

Coverage Analysis:
- Questions with good coverage: {len(coverage_analysis['well_covered'])}
- Questions needing more research: {len(coverage_analysis['gaps'])}
- Potential missing perspectives: {', '.join(coverage_analysis['missing_angles'])}

Identify specific gaps in the current research and generate targeted sub-questions and search queries to fill them."""

            # Get selected model
            selected_model = Config.SELECTED_MODEL
            client = LLMClient(model_key=selected_model)
            
            # Call LLM for refinement
            messages = [
                {"role": "system", "content": REFINEMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
            
            response = await client.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=1000
            )
            
            if not response["success"]:
                logger.error(f"Refinement LLM call failed: {response.get('error')}")
                return {
                    "success": False,
                    "error": f"LLM_ERROR: {response.get('error')}",
                    "new_sub_questions": [],
                    "new_queries": []
                }
            
            # Parse refinement response
            try:
                import json
                content = response.get("content", "")
                if not content:
                    raise ValueError("Empty response content")
                
                # Try direct JSON parsing first
                try:
                    refinement_result = json.loads(content)
                except json.JSONDecodeError:
                    # Fallback: Extract JSON from text using regex
                    import re
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        refinement_result = json.loads(json_match.group(0))
                    else:
                        raise ValueError("No valid JSON found in response")
                
                gaps_identified = refinement_result.get("gaps_identified", [])
                new_sub_questions = refinement_result.get("new_sub_questions", [])
                new_queries = refinement_result.get("new_queries", [])
                rationale = refinement_result.get("refinement_rationale", "")
                
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse refinement response: {e}")
                # Fallback refinement
                gaps_identified, new_sub_questions, new_queries = _generate_fallback_refinement(
                    original_topic, coverage_analysis
                )
                rationale = "Generated using fallback refinement due to parsing error"
            
            # Validate and clean results
            new_sub_questions = [q.strip() for q in new_sub_questions if q.strip()]
            new_queries = [q.strip() for q in new_queries if q.strip()]
            
            # Apply domain filters to new queries
            if constraints.get("include_domains") or constraints.get("exclude_domains"):
                new_queries = _apply_domain_filters_to_queries(new_queries, constraints)
            
            # Limit results
            new_sub_questions = new_sub_questions[:4]
            new_queries = new_queries[:6]
            
            logger.info(
                f"Plan refinement completed: {len(gaps_identified)} gaps identified, "
                f"{len(new_sub_questions)} new sub-questions, {len(new_queries)} new queries",
                extra={
                    "topic": original_topic,
                    "gaps_count": len(gaps_identified),
                    "new_sub_questions_count": len(new_sub_questions),
                    "new_queries_count": len(new_queries)
                }
            )
            
            emit_event(
                "plan_refinement_completed",
                metadata={
                    "topic": original_topic,
                    "gaps_identified": len(gaps_identified),
                    "new_sub_questions_count": len(new_sub_questions),
                    "new_queries_count": len(new_queries),
                    "refinement_method": "llm_guided"
                }
            )
            
            return {
                "success": True,
                "gaps_identified": gaps_identified,
                "new_sub_questions": new_sub_questions,
                "new_queries": new_queries,
                "refinement_rationale": rationale,
                "coverage_analysis": coverage_analysis,
                "metadata": {
                    "topic": original_topic,
                    "refinement_method": "llm_guided"
                }
            }
            
        except Exception as e:
            logger.error(f"Plan refinement failed: {e}")
            
            # Fallback refinement
            try:
                coverage_analysis = _analyze_coverage(original_sub_questions, claims_found, search_results)
                gaps, new_sub_questions, new_queries = _generate_fallback_refinement(
                    original_topic, coverage_analysis
                )
                
                return {
                    "success": True,
                    "gaps_identified": gaps,
                    "new_sub_questions": new_sub_questions,
                    "new_queries": new_queries,
                    "refinement_rationale": "Fallback refinement due to error",
                    "coverage_analysis": coverage_analysis,
                    "metadata": {
                        "topic": original_topic,
                        "refinement_method": "fallback",
                        "original_error": str(e)
                    }
                }
            except Exception as fallback_error:
                logger.error(f"Fallback refinement also failed: {fallback_error}")
                return {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "new_sub_questions": [],
                    "new_queries": []
                }


def _analyze_coverage(
    sub_questions: List[str],
    claims_found: List[Dict[str, Any]],
    search_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analyze how well the current research covers the planned sub-questions.
    
    Args:
        sub_questions: Original sub-questions from planning
        claims_found: Claims extracted so far
        search_results: Search results obtained
    
    Returns:
        Coverage analysis with gaps and recommendations
    """
    # Simple coverage analysis based on keyword matching
    coverage_scores = {}
    well_covered = []
    gaps = []
    
    for question in sub_questions:
        # Extract key terms from the question
        import re
        key_terms = re.findall(r'\b\w{4,}\b', question.lower())
        key_terms = [term for term in key_terms if term not in ['what', 'how', 'why', 'when', 'where', 'which']]
        
        # Count matches in claims and search results
        claim_matches = 0
        result_matches = 0
        
        for claim in claims_found:
            claim_text = claim.get('text', '').lower()
            claim_matches += sum(1 for term in key_terms if term in claim_text)
        
        for result in search_results:
            result_text = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
            result_matches += sum(1 for term in key_terms if term in result_text)
        
        total_matches = claim_matches + result_matches
        coverage_scores[question] = total_matches
        
        # Classify coverage
        if total_matches >= 3:  # Threshold for "well covered"
            well_covered.append(question)
        else:
            gaps.append(question)
    
    # Identify potential missing angles
    missing_angles = []
    topic_keywords = set()
    
    for claim in claims_found:
        words = claim.get('text', '').lower().split()
        topic_keywords.update(word for word in words if len(word) > 4)
    
    # Common research angles that might be missing
    potential_angles = [
        "historical context", "future trends", "expert opinions",
        "case studies", "comparative analysis", "regulatory aspects",
        "economic impact", "social implications", "technical details"
    ]
    
    for angle in potential_angles:
        if not any(keyword in angle for keyword in topic_keywords):
            missing_angles.append(angle)
    
    return {
        "coverage_scores": coverage_scores,
        "well_covered": well_covered,
        "gaps": gaps,
        "missing_angles": missing_angles[:5],  # Limit to top 5
        "total_claims": len(claims_found),
        "total_results": len(search_results)
    }


def _generate_fallback_refinement(
    topic: str,
    coverage_analysis: Dict[str, Any]
) -> tuple[List[str], List[str], List[str]]:
    """Generate fallback refinement when LLM refinement fails."""
    
    gaps = coverage_analysis.get('gaps', [])
    missing_angles = coverage_analysis.get('missing_angles', [])
    
    # Generate gap-focused sub-questions
    new_sub_questions = []
    for gap in gaps[:2]:  # Focus on top 2 gaps
        new_sub_questions.append(f"What additional information is available about: {gap}")
    
    for angle in missing_angles[:2]:  # Add missing angle questions
        new_sub_questions.append(f"What is the {angle} of {topic}?")
    
    # Generate targeted queries
    new_queries = []
    for gap in gaps[:2]:
        # Extract key terms from gap question
        import re
        key_terms = re.findall(r'\b\w{4,}\b', gap.lower())
        if key_terms:
            main_term = key_terms[0]
            new_queries.extend([
                f"{topic} {main_term} detailed analysis",
                f"{topic} {main_term} expert research"
            ])
    
    for angle in missing_angles[:2]:
        new_queries.append(f"{topic} {angle}")
    
    return gaps, new_sub_questions, new_queries


def _generate_fallback_plan(topic: str, constraints: Constraints) -> tuple[List[str], List[str]]:
    """Generate fallback sub-questions and queries using simple templates."""
    
    # Basic sub-questions
    sub_questions = [
        f"What is {topic}?",
        f"What are the key aspects of {topic}?",
        f"What are the current trends or developments in {topic}?",
        f"What are the implications or impacts of {topic}?",
    ]
    
    # Basic query templates
    base_queries = [
        topic,
        f'"{topic}" overview',
        f'{topic} analysis',
        f'{topic} research',
        f'{topic} trends 2024',
        f'{topic} impact',
        f'{topic} expert opinion',
    ]
    
    # Add domain-specific queries
    if constraints.get("include_domains"):
        for domain in constraints["include_domains"][:2]:  # Limit to first 2 domains
            base_queries.append(f'{topic} site:{domain}')
    
    # Add recent search if date range specified
    if constraints.get("date_range"):
        base_queries.append(f'{topic} recent {constraints["date_range"]}')
    
    return sub_questions[:4], base_queries[:8]


def _apply_domain_filters_to_queries(queries: List[str], constraints: Constraints) -> List[str]:
    """Apply domain include/exclude filters to search queries."""
    filtered_queries = []
    
    for query in queries:
        # Add site: operators for included domains
        if constraints.get("include_domains"):
            # Add a few domain-specific variants
            for domain in constraints["include_domains"][:2]:
                if not any(f"site:{domain}" in q for q in filtered_queries):
                    filtered_queries.append(f"{query} site:{domain}")
        
        # Keep original query
        filtered_queries.append(query)
    
    return filtered_queries