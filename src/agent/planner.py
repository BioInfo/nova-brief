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