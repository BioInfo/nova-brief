"""Configuration management for Nova Brief."""

import os
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from .observability.logging import get_logger

logger = get_logger(__name__)

# Load environment variables
load_dotenv()


class Config:
    """Configuration settings for Nova Brief."""
    
    # OpenRouter Configuration
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    MODEL: str = os.getenv("MODEL", "openai/gpt-oss-120b")
    
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
    def validate(cls) -> Dict[str, Any]:
        """Validate configuration and return validation report."""
        issues = []
        warnings = []
        
        # Required configurations
        if not cls.OPENROUTER_API_KEY:
            issues.append("OPENROUTER_API_KEY is required")
        
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
        return {
            "openrouter_configured": bool(cls.OPENROUTER_API_KEY),
            "model": cls.MODEL,
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