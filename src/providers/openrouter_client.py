"""Multi-provider LLM client for Nova Brief."""

import os
from typing import Any, Dict, List, Optional, Union
from openai import OpenAI

from ..config import Config, ModelConfig
from ..observability.logging import get_logger, redact_sensitive_data
from ..observability.tracing import TimedOperation, emit_event

logger = get_logger(__name__)


class LLMClient:
    """Multi-provider LLM client supporting OpenRouter, OpenAI, Anthropic, and other providers."""
    
    def __init__(
        self,
        model_key: Optional[str] = None,
        model_config: Optional[ModelConfig] = None,
        timeout: float = 30.0
    ):
        """
        Initialize LLM client with dynamic model/provider configuration.
        
        Args:
            model_key: Key for model in Config.AVAILABLE_MODELS (e.g., "gpt-4o", "claude-3.5-sonnet")
            model_config: Direct ModelConfig instance (overrides model_key)
            timeout: Request timeout in seconds
        """
        # Determine model configuration
        if model_config:
            self.model_config = model_config
        elif model_key:
            available_models = Config.get_available_models_dict()
            self.model_config = available_models.get(model_key)
            if not self.model_config:
                raise ValueError(f"Unknown model key: {model_key}")
        else:
            # Use currently selected model from config
            self.model_config = Config.get_current_model_config()
            if not self.model_config:
                # Fallback to legacy configuration
                self.model_config = ModelConfig(
                    provider="openrouter",
                    model_id=os.getenv("MODEL", "openai/gpt-oss-120b"),
                    display_name="Legacy Model",
                    api_key_env="OPENROUTER_API_KEY",
                    base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
                )
        
        self.timeout = timeout
        
        # Get API key for the configured provider
        self.api_key = os.getenv(self.model_config.api_key_env)
        if not self.api_key:
            raise ValueError(f"API key is required. Set {self.model_config.api_key_env} environment variable.")
        
        # Provider-specific client initialization
        if self.model_config.provider in ["openrouter", "openai"]:
            self._init_openai_compatible_client()
        elif self.model_config.provider == "anthropic":
            self._init_anthropic_client()
        else:
            raise ValueError(f"Unsupported provider: {self.model_config.provider}")
        
        logger.info(
            "LLM client initialized",
            extra={
                "provider": self.model_config.provider,
                "model_id": self.model_config.model_id,
                "display_name": self.model_config.display_name,
                "base_url": self.model_config.base_url,
                "timeout": timeout
            }
        )
    
    def _init_openai_compatible_client(self):
        """Initialize OpenAI-compatible client (OpenRouter or OpenAI direct)."""
        # Prepare headers
        headers = {
            "HTTP-Referer": "https://github.com/BioInfo/nova-brief",
            "X-Title": "Nova Brief Research Agent"
        }
        
        # Add provider-specific headers for OpenRouter
        if (self.model_config.provider == "openrouter" and
            self.model_config.provider_params and
            "provider" in self.model_config.provider_params):
            headers["X-OpenRouter-Provider"] = self.model_config.provider_params["provider"]
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.model_config.base_url,
            timeout=self.timeout,
            default_headers=headers
        )
    
    def _init_anthropic_client(self):
        """Initialize Anthropic client."""
        try:
            import anthropic
            self.client = anthropic.Anthropic(
                api_key=self.api_key,
                timeout=self.timeout
            )
        except ImportError:
            raise ImportError("anthropic package is required for Anthropic models. Install with: uv add anthropic")
    
    @property
    def model(self) -> str:
        """Get the model ID for the current configuration."""
        if not self.model_config:
            raise ValueError("Model configuration is not available")
        return self.model_config.model_id
    
    @property
    def provider(self) -> str:
        """Get the provider name for the current configuration."""
        if not self.model_config:
            raise ValueError("Model configuration is not available")
        return self.model_config.provider
    
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
        Send a chat completion request to the configured LLM provider.
        
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
        with TimedOperation(f"{self.provider}_chat_completion") as timer:
            try:
                # Prepare request parameters
                request_params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    **kwargs
                }
                
                # Provider-specific parameters are handled in headers for OpenRouter
                # No additional request parameters needed for provider routing
                
                if max_tokens:
                    request_params["max_tokens"] = max_tokens
                
                if response_format and self.provider != "anthropic":
                    request_params["response_format"] = response_format
                
                if tools and self.provider != "anthropic":
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
                
                # Log successful response with debug info
                content = response.choices[0].message.content if response.choices else None
                logger.info(
                    "Chat completion successful",
                    extra={
                        "response_id": response.id,
                        "model": response.model,
                        "has_content": bool(content),
                        "content_length": len(content) if content else 0,
                        "response_choices": len(response.choices),
                        **metrics
                    }
                )
                
                # Debug log for empty responses
                if not content:
                    logger.warning(
                        "Empty response content detected",
                        extra={
                            "response_id": response.id,
                            "choices_count": len(response.choices),
                            "choice_finish_reason": response.choices[0].finish_reason if response.choices else None,
                            "choice_message": str(response.choices[0].message) if response.choices else None
                        }
                    )
                
                emit_event(
                    "chat_completion_success",
                    metadata={
                        "model": response.model,
                        "provider": self.provider,
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


# Backward compatibility alias
OpenRouterClient = LLMClient


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
    client = LLMClient()
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