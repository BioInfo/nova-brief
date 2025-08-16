"""OpenRouter client with Cerebras provider pinning for Nova Brief."""

import os
from typing import Any, Dict, List, Optional, Union
from openai import OpenAI

from ..observability.logging import get_logger, redact_sensitive_data
from ..observability.tracing import TimedOperation, emit_event

logger = get_logger(__name__)


class OpenRouterClient:
    """OpenAI-compatible client for OpenRouter API with Cerebras provider pinning."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0
    ):
        """
        Initialize OpenRouter client.
        
        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            base_url: OpenRouter base URL (defaults to OPENROUTER_BASE_URL env var)
            model: Model name (defaults to MODEL env var)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.base_url = base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = model or os.getenv("MODEL", "openai/gpt-oss-120b")
        self.timeout = timeout
        
        if not self.api_key:
            raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable.")
        
        # Initialize OpenAI client with OpenRouter configuration
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=timeout
        )
        
        logger.info(
            "OpenRouter client initialized",
            extra={
                "base_url": self.base_url,
                "model": self.model,
                "timeout": timeout
            }
        )
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to OpenRouter with Cerebras provider pinning.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            response_format: Response format specification for structured output
            tools: Available tools for function calling
            tool_choice: Tool choice specification
            **kwargs: Additional parameters
        
        Returns:
            Dictionary with success status, response data, and metrics
        """
        with TimedOperation("openrouter_chat_completion") as timer:
            try:
                # Prepare request parameters with Cerebras provider pinning
                request_params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "providers": ["cerebras"],  # Pin to Cerebras provider
                    **kwargs
                }
                
                if max_tokens:
                    request_params["max_tokens"] = max_tokens
                
                if response_format:
                    request_params["response_format"] = response_format
                
                if tools:
                    request_params["tools"] = tools
                    if tool_choice:
                        request_params["tool_choice"] = tool_choice
                
                # Log request (with sensitive data redacted)
                log_params = redact_sensitive_data({
                    "model": self.model,
                    "message_count": len(messages),
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "has_response_format": bool(response_format),
                    "has_tools": bool(tools)
                })
                logger.info("Sending chat completion request", extra=log_params)
                
                # Make the API call
                response = self.client.chat.completions.create(**request_params)
                
                # Extract metrics
                usage = response.usage
                metrics = {
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0,
                    "model": response.model,
                }
                
                # Log successful response
                logger.info(
                    "Chat completion successful",
                    extra={
                        "response_id": response.id,
                        "model": response.model,
                        **metrics
                    }
                )
                
                emit_event(
                    "chat_completion_success",
                    metadata={
                        "model": response.model,
                        "provider": "cerebras",
                        **metrics
                    }
                )
                
                return {
                    "success": True,
                    "response": response,
                    "content": response.choices[0].message.content if response.choices else None,
                    "metrics": metrics
                }
                
            except Exception as e:
                logger.error(
                    f"Chat completion failed: {e}",
                    extra={
                        "error_type": type(e).__name__,
                        "model": self.model
                    }
                )
                
                emit_event(
                    "chat_completion_error",
                    metadata={
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "model": self.model
                    }
                )
                
                return {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                }


# Convenience function for backward compatibility
async def chat(
    messages: List[Dict[str, str]],
    temperature: float = 0.1,
    max_tokens: Optional[int] = None,
    response_format: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function for chat completion using default client.
    
    Args:
        messages: List of message dictionaries
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        response_format: Response format for structured output
        **kwargs: Additional parameters
    
    Returns:
        Chat completion response dictionary
    """
    client = OpenRouterClient()
    return await client.chat(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format,
        **kwargs
    )


def create_json_schema_format(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create response format specification for structured JSON output.
    
    Args:
        schema: JSON schema dictionary
    
    Returns:
        Response format specification for OpenRouter
    """
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "structured_response",
            "schema": schema,
            "strict": True
        }
    }