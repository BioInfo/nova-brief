"""
Planner agent module for breaking down research topics into actionable queries.
Generates structured research plans with sub-questions and search strategies.
"""

from typing import List, Dict, Any, Optional
from ..providers.cerebras_client import chat
from ..observability.logging import get_logger
from ..observability.tracing import start_span, end_span

logger = get_logger(__name__)


class Planner:
    """Research planning agent that decomposes topics into searchable queries."""
    
    def __init__(self):
        self.max_queries = 8
        self.planning_prompt = """You are a research planning assistant. Given a research topic, break it down into 3-6 specific, searchable sub-questions that will help gather comprehensive information about the topic.

Each sub-question should:
- Be specific and focused
- Be answerable through web search
- Cover different aspects of the main topic
- Avoid redundancy

For each sub-question, suggest 1-2 search queries that would find relevant information.

IMPORTANT: You must respond with ONLY valid JSON, no markdown, no explanations, no backticks. Start your response with {{ and end with }}.

Use this exact structure:
{{
  "research_plan": {{
    "main_topic": "the original research topic",
    "sub_questions": [
      {{
        "question": "specific sub-question",
        "rationale": "why this question is important",
        "search_queries": ["query 1", "query 2"]
      }}
    ]
  }}
}}

Research Topic: {topic}"""
    
    async def plan(self, topic: str, constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a research plan for the given topic.
        
        Args:
            topic: Research topic or question
            constraints: Optional constraints (date ranges, sources, etc.)
        
        Returns:
            Dict containing research plan with sub-questions and queries
        """
        span_id = start_span("plan", "agent", {"topic": topic})
        
        try:
            logger.info(f"Planning research for topic: {topic}")
            
            # Prepare constraints context
            constraints_text = ""
            if constraints:
                constraints_text = f"\n\nConstraints to consider:\n"
                for key, value in constraints.items():
                    constraints_text += f"- {key}: {value}\n"
            
            # Create planning prompt
            prompt = self.planning_prompt.format(topic=topic) + constraints_text
            
            # Get plan from LLM
            messages = [
                {"role": "system", "content": "You are a helpful research planning assistant."},
                {"role": "user", "content": prompt}
            ]
            
            try:
                # Call LLM without unsupported response_format
                response = chat(messages, temperature=0.1, max_tokens=1500)
                plan_text = response["content"]
                logger.info(f"LLM response received: {repr(plan_text[:100])}")
                
                # Check if response is complete
                if not plan_text or len(plan_text.strip()) < 10:
                    raise ValueError(f"Incomplete LLM response: {repr(plan_text)}")
                
                # Try to parse JSON from the response
                research_plan = self._parse_json_response(plan_text, topic)
                logger.info("Successfully parsed LLM response")
                
            except Exception as chat_error:
                logger.error(f"LLM chat failed: {chat_error}")
                # Use fallback with no LLM response
                research_plan = self._fallback_parse_plan(topic, "")
            
            # Extract all queries for easy access
            all_queries = []
            for sub_q in research_plan.get("sub_questions", []):
                all_queries.extend(sub_q.get("search_queries", []))
            
            # Limit total queries
            if len(all_queries) > self.max_queries:
                all_queries = all_queries[:self.max_queries]
                logger.info(f"Limited queries to {self.max_queries}")
            
            result = {
                "topic": topic,
                "constraints": constraints or {},
                "research_plan": research_plan,
                "all_queries": all_queries,
                "query_count": len(all_queries),
                "tokens_used": response.get("usage", {}).get("total_tokens", 0) if 'response' in locals() else 0,
                "success": True
            }
            
            logger.info(f"Research plan created: {len(research_plan.get('sub_questions', []))} sub-questions, {len(all_queries)} queries")
            end_span(span_id, success=True, additional_data={
                "sub_questions": len(research_plan.get('sub_questions', [])),
                "total_queries": len(all_queries),
                "tokens_used": response["usage"]["total_tokens"]
            })
            
            return result
            
        except Exception as e:
            error_msg = f"Planning failed for topic '{topic}': {e}"
            logger.error(error_msg)
            end_span(span_id, success=False, error=error_msg)
            return {
                "topic": topic,
                "constraints": constraints or {},
                "research_plan": {},
                "all_queries": [],
                "query_count": 0,
                "success": False,
                "error": str(e)
            }
    
    def _parse_json_response(self, response_text: str, topic: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM, with robust error handling.
        
        Args:
            response_text: Raw response from LLM
            topic: Original research topic for fallback
        
        Returns:
            Parsed research plan structure
        """
        import json
        
        # Clean up the response
        clean_text = response_text.strip()
        
        # Try to find JSON in the response
        try:
            # Look for JSON structure
            if '{' in clean_text and '}' in clean_text:
                # Extract JSON from response
                start_idx = clean_text.find('{')
                end_idx = clean_text.rfind('}') + 1
                json_text = clean_text[start_idx:end_idx]
                
                # Parse the JSON
                plan_data = json.loads(json_text)
                
                # Validate structure
                if "research_plan" in plan_data:
                    research_plan = plan_data["research_plan"]
                    
                    # Ensure required fields exist
                    if ("main_topic" in research_plan and
                        "sub_questions" in research_plan and
                        isinstance(research_plan["sub_questions"], list)):
                        logger.info(f"Successfully parsed JSON with {len(research_plan['sub_questions'])} sub-questions")
                        return research_plan
                
                raise ValueError("JSON structure doesn't match expected format")
            else:
                raise ValueError("No JSON structure found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"JSON parsing failed: {e}. Raw response: {repr(response_text[:200])}")
            # Fall back to simple parsing
            return self._fallback_parse_plan(topic, response_text)

    def _fallback_parse_plan(self, topic: str, plan_text: str) -> Dict[str, Any]:
        """
        Fallback parser for when JSON parsing fails.
        Creates a basic research plan to ensure the pipeline can continue.
        
        Args:
            topic: Original research topic
            plan_text: Raw plan text from LLM
        
        Returns:
            Basic research plan structure
        """
        logger.info("Using fallback planning due to JSON parsing failure")
        
        # Create a comprehensive but simple research plan
        questions = [
            {
                "question": f"What is {topic} and why is it important?",
                "rationale": "Understanding the basic concept and significance",
                "search_queries": [f"{topic} definition importance", f"what is {topic}"]
            },
            {
                "question": f"What are the current developments in {topic}?",
                "rationale": "Recent progress and current state",
                "search_queries": [f"{topic} recent developments 2024", f"{topic} current trends"]
            },
            {
                "question": f"What are the key challenges or considerations regarding {topic}?",
                "rationale": "Understanding limitations, challenges, or important factors",
                "search_queries": [f"{topic} challenges problems", f"{topic} considerations issues"]
            },
            {
                "question": f"What are the potential impacts or applications of {topic}?",
                "rationale": "Understanding real-world effects and uses",
                "search_queries": [f"{topic} impact applications", f"{topic} real world uses"]
            }
        ]
        
        return {
            "main_topic": topic,
            "sub_questions": questions
        }


# Global planner instance
planner = Planner()


async def plan(topic: str, constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience function for research planning."""
    return await planner.plan(topic, constraints)