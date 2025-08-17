# System Patterns *Optional*

This file documents recurring patterns and standards used in the project.
It is optional, but recommended to be updated as the project evolves.
YYYY-MM-DD HH:MM:SS - Log of updates made.

*

## Coding Patterns

*   

## Architectural Patterns

*   

## Testing Patterns

*   

---

[2025-08-16 20:10:20] - Initialized Memory Bank (created systemPatterns.md)

[2025-08-16 20:26:55] - **Multi-Provider LLM Architecture Pattern**

## Coding Patterns
- **Configuration-Driven Model Selection**: Using NamedTuple `ModelConfig` for structured model definitions
- **Provider Abstraction**: Single `LLMClient` class supporting multiple providers (OpenRouter, OpenAI, Anthropic)
- **Backward Compatibility**: Maintaining legacy environment variables while introducing new configuration system
- **UI State Management**: Streamlit session state for model selection persistence across interactions

## Architectural Patterns
- **Strategy Pattern**: Different provider initialization strategies in LLMClient based on provider type
- **Factory Pattern**: Model client creation based on configuration keys
- **Configuration Pattern**: Centralized model/provider definitions in Config class
- **Fallback Pattern**: Legacy configuration fallback when new model selection unavailable

## Testing Patterns
- **Configuration Testing**: Validation of all model configurations and API key requirements
- **Provider Testing**: LLMClient initialization testing across different model types
- **Integration Testing**: End-to-end pipeline testing with model selection
- **Backward Compatibility Testing**: Ensuring legacy configurations continue to work

[2025-08-17 00:44:00] - **Provider Routing Decoupling Pattern**

## Coding Patterns
- **Dual Model Configuration**: Creating multiple configuration entries for the same model with different routing parameters
- **Optional Provider Parameters**: Using `provider_params` field to control provider-specific routing behavior
- **Default vs Pinned Routing**: Distinguishing between OpenRouter default routing (no params) and provider-pinned routing (explicit params)
- **Clear Display Naming**: Model display names that explicitly indicate routing behavior for user transparency

## Architectural Patterns
- **Routing Strategy Pattern**: Same model can use different routing strategies based on configuration
- **Provider Transparency Pattern**: Users can choose between automated and manual provider selection
- **A/B Testing Pattern**: Facilitating performance comparisons between different routing approaches
- **Flexible Configuration Pattern**: Single model supporting multiple deployment strategies through configuration

## Testing Patterns
- **Dual Configuration Testing**: Validating both routing variants of the same model
- **Provider Parameter Testing**: Ensuring provider_params are correctly applied in API requests
- **Performance Comparison Testing**: Framework for comparing routing strategy performance
- **Configuration Isolation Testing**: Verifying that different routing configs don't interfere with each other