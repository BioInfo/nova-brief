"""Configuration management for Nova Brief."""

import os
from typing import Optional, Dict, Any, List, NamedTuple
from dotenv import load_dotenv
from .observability.logging import get_logger

logger = get_logger(__name__)

# Load environment variables
load_dotenv()


class ModelConfig(NamedTuple):
    """Configuration for a specific model."""
    provider: str  # "openrouter", "openai", "anthropic", "google"
    model_id: str
    display_name: str
    api_key_env: str
    base_url: Optional[str] = None
    provider_params: Optional[Dict[str, Any]] = None
    supports_cerebras: bool = False  # Whether this model supports Cerebras inference


class Config:
    """Configuration settings for Nova Brief."""
    
    # Base model definitions (without provider/inference specifics)
    BASE_MODELS = {
        "claude-sonnet-4": {
            "name": "Claude Sonnet 4",
            "openrouter_id": "anthropic/claude-sonnet-4",
            "direct_provider": "anthropic",
            "direct_model_id": "claude-3-5-sonnet-20241022",
            "supports_cerebras": False
        },
        "gemini-2.5-flash": {
            "name": "Gemini 2.5 Flash",
            "openrouter_id": "google/gemini-2.5-flash",
            "direct_provider": "google",
            "direct_model_id": "gemini-2.5-flash",
            "supports_cerebras": False
        },
        "gemini-2.5-pro": {
            "name": "Gemini 2.5 Pro",
            "openrouter_id": "google/gemini-2.5-pro",
            "direct_provider": "google",
            "direct_model_id": "gemini-2.5-pro",
            "supports_cerebras": False
        },
        "kimi-k2": {
            "name": "Kimi K2",
            "openrouter_id": "moonshotai/kimi-k2",
            "direct_provider": None,  # Only available via OpenRouter
            "direct_model_id": None,
            "supports_cerebras": False
        },
        "gpt-oss-120b": {
            "name": "GPT-OSS-120B",
            "openrouter_id": "openai/gpt-oss-120b",
            "direct_provider": None,  # Only available via OpenRouter
            "direct_model_id": None,
            "supports_cerebras": True
        },
        "gpt-5-mini": {
            "name": "GPT-5 Mini",
            "openrouter_id": "openai/gpt-5-mini",
            "direct_provider": "openai",
            "direct_model_id": "gpt-5-mini",
            "supports_cerebras": False
        },
        "qwen3-235b": {
            "name": "Qwen3-235B",
            "openrouter_id": "qwen/qwen3-235b-a22b-2507",
            "direct_provider": None,  # Only available via OpenRouter
            "direct_model_id": None,
            "supports_cerebras": False
        }
    }
    
    # Provider configurations
    PROVIDER_CONFIGS = {
        "openrouter": {
            "api_key_env": "OPENROUTER_API_KEY",
            "base_url": "https://openrouter.ai/api/v1"
        },
        "openai": {
            "api_key_env": "OPENAI_API_KEY",
            "base_url": "https://api.openai.com/v1"
        },
        "anthropic": {
            "api_key_env": "ANTHROPIC_API_KEY",
            "base_url": "https://api.anthropic.com"
        },
        "google": {
            "api_key_env": "GOOGLE_API_KEY",
            "base_url": "https://generativelanguage.googleapis.com/v1"
        }
    }
    
    # Generate all available model combinations dynamically
    @classmethod
    def _generate_available_models(cls) -> Dict[str, ModelConfig]:
        """Generate all available model combinations."""
        models = {}
        
        for base_key, base_config in cls.BASE_MODELS.items():
            # OpenRouter variants
            # Default inference
            models[f"{base_key}-openrouter-default"] = ModelConfig(
                provider="openrouter",
                model_id=base_config["openrouter_id"],
                display_name=f"{base_config['name']} (OpenRouter Default)",
                api_key_env=cls.PROVIDER_CONFIGS["openrouter"]["api_key_env"],
                base_url=cls.PROVIDER_CONFIGS["openrouter"]["base_url"],
                supports_cerebras=base_config["supports_cerebras"]
            )
            
            # Cerebras inference (if supported)
            if base_config["supports_cerebras"]:
                models[f"{base_key}-openrouter-cerebras"] = ModelConfig(
                    provider="openrouter",
                    model_id=base_config["openrouter_id"],
                    display_name=f"{base_config['name']} (OpenRouter + Cerebras)",
                    api_key_env=cls.PROVIDER_CONFIGS["openrouter"]["api_key_env"],
                    base_url=cls.PROVIDER_CONFIGS["openrouter"]["base_url"],
                    provider_params={"provider": "cerebras"},
                    supports_cerebras=True
                )
            
            # Direct provider variant (if available)
            if base_config["direct_provider"] and base_config["direct_model_id"]:
                direct_provider = base_config["direct_provider"]
                models[f"{base_key}-direct"] = ModelConfig(
                    provider=direct_provider,
                    model_id=base_config["direct_model_id"],
                    display_name=f"{base_config['name']} (Direct {direct_provider.title()})",
                    api_key_env=cls.PROVIDER_CONFIGS[direct_provider]["api_key_env"],
                    base_url=cls.PROVIDER_CONFIGS[direct_provider]["base_url"],
                    supports_cerebras=False
                )
        
        return models
    
    # Available Models Configuration (dynamically generated)
    @classmethod
    def get_available_models_dict(cls) -> Dict[str, ModelConfig]:
        """Get the dynamically generated available models dictionary."""
        if not hasattr(cls, '_available_models'):
            cls._available_models = cls._generate_available_models()
        return cls._available_models
    
    # Current Model Selection
    SELECTED_MODEL: str = os.getenv("SELECTED_MODEL", "gpt-oss-120b-openrouter-default")
    
    # Legacy support - maintain backward compatibility
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    MODEL: str = os.getenv("MODEL", "openai/gpt-oss-120b")  # Legacy model format
    
    # Search Configuration
    SEARCH_PROVIDER: str = os.getenv("SEARCH_PROVIDER", "duckduckgo")
    
    # Research Modes Configuration
    RESEARCH_MODES = {
        "🚀 Quick Brief": {
            "description": "Fast, high-level overview with essential information",
            "goal": "Get a rapid, comprehensive overview in minimum time",
            "settings": {
                "max_rounds": 1,
                "per_domain_cap": 2,
                "fetch_timeout_s": 10.0,
                "target_word_count": "400-600 words",
                "search_strategy": "fast"
            },
            "model_preference": "balanced"  # Can be "speed", "balanced", or "quality"
        },
        "⚖️ Balanced Analysis": {
            "description": "Thorough research with balanced speed and depth",
            "goal": "Comprehensive analysis with good balance of speed and quality",
            "settings": {
                "max_rounds": 3,
                "per_domain_cap": 3,
                "fetch_timeout_s": 15.0,
                "target_word_count": "800-1200 words",
                "search_strategy": "balanced"
            },
            "model_preference": "balanced"
        },
        "🔬 Deep Dive": {
            "description": "Comprehensive, in-depth analysis prioritizing completeness",
            "goal": "Maximum depth and quality with extensive source coverage",
            "settings": {
                "max_rounds": 5,
                "per_domain_cap": 5,
                "fetch_timeout_s": 20.0,
                "target_word_count": "1500-2000 words",
                "search_strategy": "comprehensive"
            },
            "model_preference": "quality"
        }
    }
    
    # Default Research Mode
    SELECTED_RESEARCH_MODE: str = os.getenv("RESEARCH_MODE", "⚖️ Balanced Analysis")
    
    # Heterogeneous Agent Policies Configuration
    AGENT_POLICIES = {
        "planner": {
            "description": "Research planning and query generation",
            "model_requirements": {
                "reasoning": "high",
                "speed": "medium",
                "cost": "low"
            },
            "preferred_models": {
                "speed": ["gpt-oss-120b-openrouter-cerebras", "gemini-2.5-flash-openrouter-default"],
                "balanced": ["gpt-oss-120b-openrouter-default", "gemini-2.5-flash-openrouter-default"],
                "quality": ["claude-sonnet-4-openrouter-default", "gemini-2.5-pro-openrouter-default"]
            },
            "fallback_models": ["gpt-oss-120b-openrouter-default"],
            "temperature": 0.3,
            "max_tokens": 1000
        },
        "searcher": {
            "description": "Web search and result gathering (no LLM usage)",
            "model_requirements": {},
            "preferred_models": {},
            "fallback_models": [],
            "llm_required": False
        },
        "reader": {
            "description": "Content extraction and text processing",
            "model_requirements": {
                "text_processing": "high",
                "speed": "high",
                "cost": "low"
            },
            "preferred_models": {
                "speed": ["gpt-oss-120b-openrouter-cerebras", "gemini-2.5-flash-openrouter-default"],
                "balanced": ["gpt-oss-120b-openrouter-default", "gemini-2.5-flash-openrouter-default"],
                "quality": ["gpt-oss-120b-openrouter-default", "gemini-2.5-pro-openrouter-default"]
            },
            "fallback_models": ["gpt-oss-120b-openrouter-default"],
            "temperature": 0.1,
            "max_tokens": 2000
        },
        "analyst": {
            "description": "Content analysis and claim extraction",
            "model_requirements": {
                "reasoning": "very_high",
                "analytical_thinking": "very_high",
                "structured_output": "high",
                "speed": "medium"
            },
            "preferred_models": {
                "speed": ["gpt-oss-120b-openrouter-default", "gemini-2.5-flash-openrouter-default"],
                "balanced": ["claude-sonnet-4-openrouter-default", "gemini-2.5-pro-openrouter-default"],
                "quality": ["claude-sonnet-4-openrouter-default", "gemini-2.5-pro-openrouter-default"]
            },
            "fallback_models": ["gpt-oss-120b-openrouter-default"],
            "temperature": 0.1,
            "max_tokens": 2000
        },
        "verifier": {
            "description": "Fact verification and source validation",
            "model_requirements": {
                "reasoning": "very_high",
                "fact_checking": "very_high",
                "critical_thinking": "very_high",
                "speed": "low"
            },
            "preferred_models": {
                "speed": ["claude-sonnet-4-openrouter-default", "gemini-2.5-pro-openrouter-default"],
                "balanced": ["claude-sonnet-4-openrouter-default", "gemini-2.5-pro-openrouter-default"],
                "quality": ["claude-sonnet-4-openrouter-default", "gemini-2.5-pro-openrouter-default"]
            },
            "fallback_models": ["gpt-oss-120b-openrouter-default"],
            "temperature": 0.0,
            "max_tokens": 1500
        },
        "writer": {
            "description": "Report generation and content writing",
            "model_requirements": {
                "writing_quality": "very_high",
                "creativity": "medium",
                "structured_output": "high",
                "audience_adaptation": "high"
            },
            "preferred_models": {
                "speed": ["gpt-oss-120b-openrouter-default", "gemini-2.5-flash-openrouter-default"],
                "balanced": ["claude-sonnet-4-openrouter-default", "gemini-2.5-pro-openrouter-default"],
                "quality": ["claude-sonnet-4-openrouter-default", "gemini-2.5-pro-openrouter-default"]
            },
            "fallback_models": ["gpt-oss-120b-openrouter-default"],
            "temperature": 0.2,
            "max_tokens": 3000,
            "audience_specific": {
                "Executive": {
                    "preferred_models": {
                        "speed": ["claude-sonnet-4-openrouter-default"],
                        "balanced": ["claude-sonnet-4-openrouter-default"],
                        "quality": ["claude-sonnet-4-openrouter-default"]
                    },
                    "temperature": 0.2
                },
                "Technical": {
                    "preferred_models": {
                        "speed": ["gemini-2.5-pro-openrouter-default", "claude-sonnet-4-openrouter-default"],
                        "balanced": ["gemini-2.5-pro-openrouter-default", "claude-sonnet-4-openrouter-default"],
                        "quality": ["gemini-2.5-pro-openrouter-default", "claude-sonnet-4-openrouter-default"]
                    },
                    "temperature": 0.1
                },
                "General": {
                    "preferred_models": {
                        "speed": ["gpt-oss-120b-openrouter-default", "gemini-2.5-flash-openrouter-default"],
                        "balanced": ["claude-sonnet-4-openrouter-default", "gemini-2.5-pro-openrouter-default"],
                        "quality": ["claude-sonnet-4-openrouter-default", "gemini-2.5-pro-openrouter-default"]
                    },
                    "temperature": 0.3
                }
            }
        },
        "critic": {
            "description": "Report quality assurance and review feedback",
            "model_requirements": {
                "reasoning": "very_high",
                "critical_thinking": "very_high",
                "structured_output": "very_high",
                "analytical_thinking": "very_high"
            },
            "preferred_models": {
                "speed": ["claude-sonnet-4-openrouter-default", "gemini-2.5-pro-openrouter-default"],
                "balanced": ["claude-sonnet-4-openrouter-default", "gemini-2.5-pro-openrouter-default"],
                "quality": ["claude-sonnet-4-openrouter-default", "gemini-2.5-pro-openrouter-default"]
            },
            "fallback_models": ["gpt-oss-120b-openrouter-default"],
            "temperature": 0.1,
            "max_tokens": 2500,
            "audience_specific": {
                "Executive": {
                    "preferred_models": {
                        "speed": ["claude-sonnet-4-openrouter-default"],
                        "balanced": ["claude-sonnet-4-openrouter-default"],
                        "quality": ["claude-sonnet-4-openrouter-default"]
                    },
                    "temperature": 0.1
                },
                "Technical": {
                    "preferred_models": {
                        "speed": ["gemini-2.5-pro-openrouter-default", "claude-sonnet-4-openrouter-default"],
                        "balanced": ["gemini-2.5-pro-openrouter-default", "claude-sonnet-4-openrouter-default"],
                        "quality": ["gemini-2.5-pro-openrouter-default", "claude-sonnet-4-openrouter-default"]
                    },
                    "temperature": 0.05
                },
                "General": {
                    "preferred_models": {
                        "speed": ["claude-sonnet-4-openrouter-default", "gemini-2.5-pro-openrouter-default"],
                        "balanced": ["claude-sonnet-4-openrouter-default", "gemini-2.5-pro-openrouter-default"],
                        "quality": ["claude-sonnet-4-openrouter-default", "gemini-2.5-pro-openrouter-default"]
                    },
                    "temperature": 0.1
                }
            }
        }
    }
    
    # Agent Configuration (legacy - now driven by research modes)
    MAX_ROUNDS: int = int(os.getenv("MAX_ROUNDS", "3"))
    PER_DOMAIN_CAP: int = int(os.getenv("PER_DOMAIN_CAP", "3"))
    FETCH_TIMEOUT_S: float = float(os.getenv("FETCH_TIMEOUT_S", "15.0"))
    
    # Feature Flags
    ENABLE_CACHE: bool = os.getenv("ENABLE_CACHE", "false").lower() == "true"
    
    # System Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    USER_AGENT: str = os.getenv("USER_AGENT", "NovaBrief-Research/0.1")
    
    @classmethod
    def get_current_model_config(cls) -> Optional[ModelConfig]:
        """Get configuration for the currently selected model."""
        available_models = cls.get_available_models_dict()
        return available_models.get(cls.SELECTED_MODEL)
    
    @classmethod
    def get_available_models(cls) -> List[str]:
        """Get list of available model keys."""
        return list(cls.get_available_models_dict().keys())
    
    @classmethod
    def get_models_by_provider(cls, provider: str) -> Dict[str, ModelConfig]:
        """Get models filtered by provider."""
        available_models = cls.get_available_models_dict()
        return {
            key: config for key, config in available_models.items()
            if config.provider == provider
        }
    
    @classmethod
    def get_models_by_base_model(cls, base_model: str) -> Dict[str, ModelConfig]:
        """Get all variants of a base model."""
        available_models = cls.get_available_models_dict()
        return {
            key: config for key, config in available_models.items()
            if key.startswith(base_model)
        }
    
    @classmethod
    def get_cerebras_supported_models(cls) -> Dict[str, ModelConfig]:
        """Get models that support Cerebras inference."""
        available_models = cls.get_available_models_dict()
        return {
            key: config for key, config in available_models.items()
            if config.supports_cerebras
        }
    
    @classmethod
    def validate_model_config(cls, model_key: str) -> Dict[str, Any]:
        """Validate configuration for a specific model."""
        issues = []
        warnings = []
        available_models = cls.get_available_models_dict()
        
        if model_key not in available_models:
            issues.append(f"Unknown model: {model_key}")
            return {"valid": False, "issues": issues, "warnings": warnings}
        
        model_config = available_models[model_key]
        api_key = os.getenv(model_config.api_key_env)
        
        if not api_key:
            issues.append(f"Missing API key: {model_config.api_key_env}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "model_config": model_config
        }
    
    @classmethod
    def validate(cls) -> Dict[str, Any]:
        """Validate configuration and return validation report."""
        issues = []
        warnings = []
        
        # Validate current model selection
        model_validation = cls.validate_model_config(cls.SELECTED_MODEL)
        issues.extend(model_validation["issues"])
        warnings.extend(model_validation["warnings"])
        
        # Legacy validation for backward compatibility
        if not model_validation["valid"] and not cls.OPENROUTER_API_KEY:
            issues.append("No valid model configuration found and OPENROUTER_API_KEY is missing")
        
        # Validation checks
        if cls.MAX_ROUNDS < 1:
            issues.append("MAX_ROUNDS must be at least 1")
        
        if cls.PER_DOMAIN_CAP < 1:
            issues.append("PER_DOMAIN_CAP must be at least 1")
        
        if cls.FETCH_TIMEOUT_S < 5:
            warnings.append("FETCH_TIMEOUT_S less than 5 seconds may cause timeouts")
        
        # Log validation results
        if issues:
            for issue in issues:
                logger.error(f"Configuration error: {issue}")
        
        if warnings:
            for warning in warnings:
                logger.warning(f"Configuration warning: {warning}")
        
        if not issues and not warnings:
            logger.info("Configuration validation passed")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }
    
    @classmethod
    def get_research_modes(cls) -> Dict[str, Dict[str, Any]]:
        """Get available research modes."""
        return cls.RESEARCH_MODES
    
    @classmethod
    def get_research_mode_config(cls, mode_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific research mode."""
        return cls.RESEARCH_MODES.get(mode_name)
    
    @classmethod
    def apply_research_mode(cls, mode_name: str) -> Dict[str, Any]:
        """Apply research mode settings and return constraints."""
        mode_config = cls.get_research_mode_config(mode_name)
        if not mode_config:
            raise ValueError(f"Unknown research mode: {mode_name}")
        
        settings = mode_config["settings"]
        
        # Return constraints object compatible with existing pipeline
        return {
            "date_range": None,
            "include_domains": [],
            "exclude_domains": [],
            "max_rounds": settings["max_rounds"],
            "per_domain_cap": settings["per_domain_cap"],
            "fetch_timeout_s": settings["fetch_timeout_s"],
            "max_tokens_per_chunk": 1000,
            # Additional research mode specific settings
            "_research_mode": mode_name,
            "_target_word_count": settings["target_word_count"],
            "_search_strategy": settings["search_strategy"],
            "_model_preference": mode_config["model_preference"]
        }
    
    @classmethod
    def get_agent_model(
        cls,
        agent_name: str,
        model_preference: str = "balanced",
        target_audience: Optional[str] = None
    ) -> Optional[str]:
        """
        Get the optimal model for a specific agent based on policies and preferences.
        
        Args:
            agent_name: Name of the agent ("planner", "analyst", "writer", etc.)
            model_preference: Preference level ("speed", "balanced", "quality")
            target_audience: For writer agent, specific audience ("Executive", "Technical", "General")
        
        Returns:
            Model key string, or None if agent doesn't require LLM
        """
        if agent_name not in cls.AGENT_POLICIES:
            logger.warning(f"Unknown agent: {agent_name}, falling back to default model")
            return cls.SELECTED_MODEL
        
        agent_policy = cls.AGENT_POLICIES[agent_name]
        
        # Check if agent requires LLM
        if not agent_policy.get("llm_required", True):
            return None
        
        # Handle audience-specific models for writer
        if agent_name == "writer" and target_audience:
            audience_config = agent_policy.get("audience_specific", {}).get(target_audience)
            if audience_config:
                preferred_models = audience_config.get("preferred_models", {}).get(model_preference, [])
                if preferred_models:
                    # Return first available model
                    available_models = cls.get_available_models()
                    for model in preferred_models:
                        if model in available_models:
                            validation = cls.validate_model_config(model)
                            if validation["valid"]:
                                return model
        
        # Get standard preferred models for this agent
        preferred_models = agent_policy.get("preferred_models", {}).get(model_preference, [])
        available_models = cls.get_available_models()
        
        # Find first available and valid preferred model
        for model in preferred_models:
            if model in available_models:
                validation = cls.validate_model_config(model)
                if validation["valid"]:
                    return model
        
        # Fall back to agent's fallback models
        fallback_models = agent_policy.get("fallback_models", [])
        for model in fallback_models:
            if model in available_models:
                validation = cls.validate_model_config(model)
                if validation["valid"]:
                    return model
        
        # Ultimate fallback to global default
        return cls.SELECTED_MODEL
    
    @classmethod
    def get_agent_parameters(
        cls,
        agent_name: str,
        target_audience: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get optimal parameters for a specific agent.
        
        Args:
            agent_name: Name of the agent
            target_audience: For writer agent, specific audience
        
        Returns:
            Dictionary with temperature, max_tokens, and other parameters
        """
        if agent_name not in cls.AGENT_POLICIES:
            return {"temperature": 0.3, "max_tokens": 1000}
        
        agent_policy = cls.AGENT_POLICIES[agent_name]
        
        # Base parameters
        params = {
            "temperature": agent_policy.get("temperature", 0.3),
            "max_tokens": agent_policy.get("max_tokens", 1000)
        }
        
        # Override with audience-specific parameters for writer
        if agent_name == "writer" and target_audience:
            audience_config = agent_policy.get("audience_specific", {}).get(target_audience, {})
            if "temperature" in audience_config:
                params["temperature"] = audience_config["temperature"]
            if "max_tokens" in audience_config:
                params["max_tokens"] = audience_config["max_tokens"]
        
        return params
    
    @classmethod
    def get_agent_policy(cls, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get the complete policy configuration for an agent."""
        return cls.AGENT_POLICIES.get(agent_name)
    
    @classmethod
    def list_agent_models(cls, agent_name: str, model_preference: str = "balanced") -> List[str]:
        """
        List all suitable models for an agent in preference order.
        
        Args:
            agent_name: Name of the agent
            model_preference: Preference level
        
        Returns:
            List of model keys in preference order
        """
        if agent_name not in cls.AGENT_POLICIES:
            return [cls.SELECTED_MODEL]
        
        agent_policy = cls.AGENT_POLICIES[agent_name]
        
        if not agent_policy.get("llm_required", True):
            return []
        
        models = []
        available_models = set(cls.get_available_models())
        
        # Add preferred models
        preferred = agent_policy.get("preferred_models", {}).get(model_preference, [])
        for model in preferred:
            if model in available_models:
                validation = cls.validate_model_config(model)
                if validation["valid"]:
                    models.append(model)
        
        # Add fallback models
        fallbacks = agent_policy.get("fallback_models", [])
        for model in fallbacks:
            if model in available_models and model not in models:
                validation = cls.validate_model_config(model)
                if validation["valid"]:
                    models.append(model)
        
        return models
    
    @classmethod
    def validate_agent_policies(cls) -> Dict[str, Any]:
        """Validate all agent policies and return validation report."""
        issues = []
        warnings = []
        available_models = set(cls.get_available_models())
        
        for agent_name, policy in cls.AGENT_POLICIES.items():
            # Check if agent requires LLM but has no valid models
            if policy.get("llm_required", True):
                has_valid_model = False
                
                # Check preferred models
                for preference in ["speed", "balanced", "quality"]:
                    preferred_models = policy.get("preferred_models", {}).get(preference, [])
                    for model in preferred_models:
                        if model in available_models:
                            validation = cls.validate_model_config(model)
                            if validation["valid"]:
                                has_valid_model = True
                                break
                    if has_valid_model:
                        break
                
                # Check fallback models if no preferred models found
                if not has_valid_model:
                    fallback_models = policy.get("fallback_models", [])
                    for model in fallback_models:
                        if model in available_models:
                            validation = cls.validate_model_config(model)
                            if validation["valid"]:
                                has_valid_model = True
                                break
                
                if not has_valid_model:
                    issues.append(f"Agent '{agent_name}' has no valid models available")
            
            # Check for missing required parameters
            if "temperature" not in policy and policy.get("llm_required", True):
                warnings.append(f"Agent '{agent_name}' missing temperature parameter")
            
            if "max_tokens" not in policy and policy.get("llm_required", True):
                warnings.append(f"Agent '{agent_name}' missing max_tokens parameter")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }
    
    @classmethod
    def get_summary(cls) -> Dict[str, Any]:
        """Get configuration summary for logging/debugging."""
        current_model = cls.get_current_model_config()
        
        return {
            "selected_model": cls.SELECTED_MODEL,
            "selected_research_mode": cls.SELECTED_RESEARCH_MODE,
            "model_display_name": current_model.display_name if current_model else "Unknown",
            "provider": current_model.provider if current_model else "Unknown",
            "model_id": current_model.model_id if current_model else cls.MODEL,
            "api_key_configured": bool(os.getenv(current_model.api_key_env)) if current_model else bool(cls.OPENROUTER_API_KEY),
            "search_provider": cls.SEARCH_PROVIDER,
            "max_rounds": cls.MAX_ROUNDS,
            "per_domain_cap": cls.PER_DOMAIN_CAP,
            "fetch_timeout": cls.FETCH_TIMEOUT_S,
            "cache_enabled": cls.ENABLE_CACHE,
            "log_level": cls.LOG_LEVEL,
            "agent_policies_count": len(cls.AGENT_POLICIES)
        }


def get_config() -> Config:
    """Get configuration instance."""
    return Config()


def validate_environment() -> bool:
    """Validate environment setup."""
    config = get_config()
    validation = config.validate()
    
    if not validation["valid"]:
        logger.error("Environment validation failed")
        return False
    
    logger.info("Environment validation passed")
    return True


def setup_environment_for_development():
    """Setup environment for development (called by setup scripts)."""
    env_file = ".env"
    env_example = ".env.example"
    
    if not os.path.exists(env_file):
        if os.path.exists(env_example):
            logger.info(f"Creating {env_file} from {env_example}")
            # Copy example to .env for development
            with open(env_example, 'r') as example:
                content = example.read()
            
            with open(env_file, 'w') as env:
                env.write(content)
            
            logger.warning(f"Created {env_file} - please update with your API keys")
        else:
            logger.error(f"No {env_example} found - cannot setup environment")
            return False
    
    return True