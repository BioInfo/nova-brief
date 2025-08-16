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

Format your response as a JSON object with this structure:
{
  "research_plan": {
    "main_topic": "the original research topic",
    "sub_questions": [
      {
        "question": "specific sub-question",
        "rationale": "why this question is important",
        "search_queries": ["query 1", "query 2"]
      }
    ]
  }
}

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
            
            response = chat(messages, temperature=0.3, max_tokens=1500)
            plan_text = response["content"]
            
            # Parse the JSON response
            import json
            try:
                plan_data = json.loads(plan_text)
                research_plan = plan_data.get("research_plan", {})
            except json.JSONDecodeError:
                # Fallback to simple parsing if JSON fails
                logger.warning("Failed to parse JSON plan, using fallback")
                research_plan = self._fallback_parse_plan(topic, plan_text)
            
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
                "tokens_used": response["usage"]["total_tokens"],
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
    
    def _fallback_parse_plan(self, topic: str, plan_text: str) -> Dict[str, Any]:
        """
        Fallback parser for when JSON parsing fails.
        
        Args:
            topic: Original research topic
            plan_text: Raw plan text from LLM
        
        Returns:
            Simplified research plan structure
        """
        # Simple fallback - extract questions and create basic queries
        lines = plan_text.split('\n')
        questions = []
        
        for line in lines:
            line = line.strip()
            if line and ('?' in line or 'question' in line.lower()):
                # Clean up the line to extract question
                question = line.replace('-', '').replace('*', '').strip()
                if question:
                    # Generate simple search queries based on question
                    search_queries = [question, f"{topic} {question}"]
                    questions.append({
                        "question": question,
                        "rationale": "Generated from fallback parsing",
                        "search_queries": search_queries[:2]
                    })
        
        # If no questions found, create basic ones
        if not questions:
            questions = [
                {
                    "question": f"What is {topic}?",
                    "rationale": "Basic definition and overview",
                    "search_queries": [topic, f"{topic} definition overview"]
                },
                {
                    "question": f"Recent developments in {topic}",
                    "rationale": "Current state and recent changes",
                    "search_queries": [f"{topic} recent developments", f"{topic} 2024 news"]
                }
            ]
        
        return {
            "main_topic": topic,
            "sub_questions": questions[:6]  # Limit to 6 questions
        }


# Global planner instance
planner = Planner()


async def plan(topic: str, constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience function for research planning."""
    return await planner.plan(topic, constraints)