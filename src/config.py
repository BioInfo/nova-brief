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
    
    # Agent Configuration
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
    def get_summary(cls) -> Dict[str, Any]:
        """Get configuration summary for logging/debugging."""
        current_model = cls.get_current_model_config()
        
        return {
            "selected_model": cls.SELECTED_MODEL,
            "model_display_name": current_model.display_name if current_model else "Unknown",
            "provider": current_model.provider if current_model else "Unknown",
            "model_id": current_model.model_id if current_model else cls.MODEL,
            "api_key_configured": bool(os.getenv(current_model.api_key_env)) if current_model else bool(cls.OPENROUTER_API_KEY),
            "search_provider": cls.SEARCH_PROVIDER,
            "max_rounds": cls.MAX_ROUNDS,
            "per_domain_cap": cls.PER_DOMAIN_CAP,
            "fetch_timeout": cls.FETCH_TIMEOUT_S,
            "cache_enabled": cls.ENABLE_CACHE,
            "log_level": cls.LOG_LEVEL
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