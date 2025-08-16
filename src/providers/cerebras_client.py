"""
Cerebras client provider for LLM interactions.
Uses OpenAI-compatible API to communicate with Cerebras Inference Cloud.
"""

import os
from typing import Dict, List, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv
import logging

# Load environment variables from both .env and .env.local
load_dotenv()  # Load .env
load_dotenv('.env.local')  # Load .env.local (overrides .env if present)

logger = logging.getLogger(__name__)


class CerebrasClient:
    """OpenAI-compatible client for Cerebras Inference Cloud."""
    
    def __init__(self):
        self.api_key = os.getenv("CEREBRAS_API_KEY")
        self.base_url = os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1")
        self.model = os.getenv("MODEL", "gpt-oss-120b")
        
        # Initialize client only if API key is available
        self.client = None
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """
        Send chat completion request to Cerebras.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
        
        Returns:
            Dict containing response content and metadata
        """
        if not self.client:
            raise ValueError("CEREBRAS_API_KEY environment variable is required")
            
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                **kwargs
            )
            
            return {
                "content": response.choices[0].message.content,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
                "model": response.model,
                "finish_reason": response.choices[0].finish_reason
            }
        except Exception as e:
            logger.error(f"Cerebras API error: {e}")
            raise


# Global instance - will be created without failing even if no API key
cerebras_client = CerebrasClient()


def chat(messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
    """Convenience function for chat completions."""
    return cerebras_client.chat(messages, **kwargs)