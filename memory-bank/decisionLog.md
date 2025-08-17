# Decision Log

This file records architectural and implementation decisions using a list format.
YYYY-MM-DD HH:MM:SS - Log of updates made.

*

## Decision

*   

## Rationale 

*   

## Implementation Details

*   

---

[2025-08-16 20:09:55] - Initialized Memory Bank (created decisionLog.md)

[2025-08-16 20:26:15] - **Refactored LLM Provider Architecture for Configurable Models**

## Decision
Refactored Nova Brief application to support multiple LLM providers and models through UI selection and environment variables, removing the hardcoded dependency on openai/gpt-oss-120b and Cerebras provider.

## Rationale
- **Flexibility**: Users can now experiment with different powerful models (GPT-4o, Claude 3.5 Sonnet, etc.)
- **Provider Independence**: Support for OpenRouter, direct OpenAI, and Anthropic APIs
- **Future-Proofing**: Easy to add new models and providers as they become available
- **User Experience**: UI-based model selection with real-time API key validation

## Implementation Details
- Created `ModelConfig` class for structured model/provider definitions
- Updated `Config` class with `AVAILABLE_MODELS` dictionary containing 7 predefined models
- Replaced `OpenRouterClient` with multi-provider `LLMClient` class
- Added UI components for model selection in Streamlit interface
- Updated agent pipeline to use selected model through configuration
- Maintained backward compatibility with existing environment variables
- Updated documentation and examples for new model selection system

## Models Supported
- OpenRouter: gpt-oss-120b (Cerebras), gpt-4o, gpt-4o-mini, claude-3.5-sonnet, claude-3-haiku
- Direct APIs: gpt-4o-direct (OpenAI), claude-3.5-sonnet-direct (Anthropic)

## Migration Path
- Existing users continue to work with default gpt-oss-120b
- New users can select models via UI or SELECTED_MODEL environment variable
- Legacy MODEL environment variable still supported for backward compatibility

[2025-08-17 00:44:00] - **Decoupled Model Selection from Provider Routing for GPT-OSS-120B**

## Decision
Refactored Nova Brief application to completely decouple LLM model selection from provider selection, specifically enabling users to select openai/gpt-oss-120b with either Cerebras provider pinning or OpenRouter's default routing.

## Rationale
- **Performance Testing**: Users can now conduct true performance comparisons between provider-pinned and default-routed requests for the same model
- **Flexibility**: Enables testing different routing strategies for identical models without changing the underlying model configuration
- **User Choice**: Provides transparent control over whether to use provider-specific optimizations or let OpenRouter handle routing
- **A/B Testing**: Facilitates comparative analysis of Cerebras-pinned vs default-routed performance for gpt-oss-120b

## Implementation Details
- Split `gpt-oss-120b` configuration into two variants:
  - `gpt-oss-120b`: Uses OpenRouter default routing (no provider_params)
  - `gpt-oss-120b-cerebras`: Pins to Cerebras provider (provider_params={"provider": "cerebras"})
- Updated display names to clearly indicate routing behavior
- Maintained backward compatibility with existing LLMClient implementation
- UI automatically displays both options with clear labeling
- All existing functionality preserved while adding new routing flexibility

## Impact
- Users can now select same model with different routing strategies
- Enables direct performance comparisons between Cerebras-pinned and default routing
- No breaking changes to existing API or configuration
- Enhanced transparency in provider selection process

[2025-08-17 00:56:00] - **Implemented Comprehensive Model+Provider+Inference Selection System**

## Decision
Expanded the Nova Brief application to support full flexibility in model selection, allowing users to choose any combination of model, provider (OpenRouter vs Direct), and inference method (Cerebras vs Default routing).

## Rationale
- **Maximum Flexibility**: Users can now select from 7 different base models with multiple routing options
- **Provider Choice**: Support for both OpenRouter aggregation and direct provider APIs
- **Inference Optimization**: Cerebras inference available for supported models (GPT-OSS-120B)
- **Comprehensive Coverage**: All requested models included: Claude Sonnet 4, Gemini 2.5 Flash/Pro, Kimi K2, GPT-OSS-120B, GPT-5 Mini, Qwen3-235B

## Implementation Details
- Created dynamic model configuration system generating 12 total model combinations
- Added support for 4 providers: OpenRouter, OpenAI, Anthropic, Google
- Implemented BASE_MODELS dictionary for model definitions with provider mappings
- Enhanced UI with organized model selection showing provider and inference details
- Updated .env.example with all required API keys and clear documentation
- Added API key status indicators and setup guidance for each provider

## Model Combinations Available
### OpenRouter Models (8 total):
- claude-sonnet-4-openrouter-default
- gemini-2.5-flash-openrouter-default, gemini-2.5-pro-openrouter-default
- kimi-k2-openrouter-default
- gpt-oss-120b-openrouter-default, gpt-oss-120b-openrouter-cerebras (🧠)
- gpt-5-mini-openrouter-default
- qwen3-235b-openrouter-default

### Direct Provider Models (4 total):
- claude-sonnet-4-direct (Anthropic)
- gemini-2.5-flash-direct, gemini-2.5-pro-direct (Google)
- gpt-5-mini-direct (OpenAI)

## User Experience
- Organized UI showing models grouped by base model with clear provider/inference indicators
- Enhanced API status panel showing required API keys with setup links
- Real-time validation and guidance for missing API keys
- Clear indication of Cerebras inference availability

## Impact
- Complete decoupling of model, provider, and inference selection
- Enables comprehensive A/B testing across all combinations
- Provides flexibility for cost optimization and performance testing
- Future-proof architecture for easy addition of new models and providers

[2025-08-17 01:22:15] - **Implemented Multi-Model Evaluation Harness for Comparative Analysis**

## Decision
Created a comprehensive multi-model evaluation harness that enables comparing 1-5 model/routing/provider combinations simultaneously, providing detailed comparative metrics and rankings for performance analysis.

## Rationale
- **Enhanced Evaluation Capabilities**: Users can now conduct true A/B testing across different models, providers, and routing strategies
- **Comparative Analysis**: Provides detailed rankings by speed, quality (coverage), reliability (success rate), and verbosity
- **Flexible Configuration**: Supports predefined comparison sets (default, quick, comprehensive) and custom model selections
- **Performance Insights**: Enables identification of optimal model configurations for different use cases
- **Cost-Benefit Analysis**: Allows evaluation of performance trade-offs between different model/provider combinations

## Implementation Details
- Created `MultiModelEvaluationHarness` class in `eval/multi_model_harness.py`
- Supports 1-5 model comparison with comprehensive metrics calculation
- Default comparison set: GPT-OSS-120B (Cerebras), GPT-OSS-120B (Default), Claude Sonnet 4
- Quick comparison set: GPT-OSS-120B (Cerebras) vs GPT-OSS-120B (Default)
- Comprehensive comparison set: 5 models across different providers and sizes
- Added statistical analysis including means, standard deviations, and comparative rankings
- Created convenience script `tools/scripts/run_model_comparison.sh` for easy usage
- Maintains compatibility with existing single-model evaluation harness

## Comparative Metrics Provided
- **Speed Ranking**: Average duration per topic (lower is better)
- **Quality Ranking**: Coverage score based on expected content elements (higher is better)
- **Reliability Ranking**: Success rate across topics (higher is better)
- **Verbosity Ranking**: Average word count per report (for analysis purposes)
- **Cross-Model Statistics**: Standard deviations and variability metrics
- **Detailed Results**: Complete topic-by-topic breakdown for each model

## Usage Examples
- `uv run python eval/multi_model_harness.py --comparison-set default`
- `uv run python eval/multi_model_harness.py --models gpt-oss-120b-openrouter-cerebras,claude-sonnet-4-openrouter-default`
- `./tools/scripts/run_model_comparison.sh --quick --topics 2`
- `./tools/scripts/run_model_comparison.sh --set comprehensive`

## Impact
- Enables data-driven model selection based on performance requirements
- Facilitates optimization of model configurations for specific use cases
- Provides foundation for continuous performance monitoring and improvement
- Supports research into optimal routing strategies and provider selection
[2025-08-17 11:21:20] - **Adopted Stage 1.5 — Polish & Performance; retain Streamlit UI for this stage**

## Decision
Introduce an intermediate delivery phase, "Stage 1.5 — Polish & Performance," between Stage 1 (MVP) and Stage 2 (Core robustness). Continue using Streamlit for the UI during Stage 1.5.

## Rationale 
- Improve user experience and perceived performance before adding new architectural complexity.
- Provide real-time progress visibility and refined results layout to reduce user uncertainty.
- Accelerate reading throughput via async fetching to reduce end-to-end latency.
- Establish quality safeguards (Content Quality Gate) to ensure higher-quality inputs to downstream agents.
- Surface evaluation insights in-app via Model Benchmarks to inform model/provider choices.

## Implementation Details
- docs/master-plan.md updated with Stage 1.5 scope, tasks, and renumbered weeks.
- docs/prd.md updated with a Stage 1.5 section and adjusted implementation plan.
- docs/specs/evaluation-harness.md expanded with sub_question_coverage metric and notes.
- docs/specs/module-specs.md augmented with a Reader Content Quality Gate and Stage 1.5 async I/O.
- README.md roadmap updated to include Stage 1.5 and feature list.
- UI enhancements: progress bar with status/percent, ETA, tabs for Report/Metrics/Sources/Export, Sources expanders.
- Reader: httpx.AsyncClient + asyncio.gather for parallel fetch, Content Quality Gate.
- Data model: partial_failures added in ResearchState at Stage 1.5 to record non-fatal errors.

## Impact
- Faster, clearer runs with improved status transparency.
- Better input quality for analyst/verifier stages.
- In-app visibility of evaluation results to guide model selection.

[2025-08-17 07:52:27] - Stage 1.5 Real-Time Progress Implementation
**Decision:** Implemented callback-based progress tracking system in orchestrator
**Rationale:** Required real-time UI updates without polling. Each pipeline stage now calls progress_callback with updated ResearchState
**Implementation:** Modified run_research_pipeline() to accept optional progress_callback parameter, updated all stage functions to call notify_progress()
**Impact:** Enables live progress bars, ETA calculation, and status updates in Streamlit UI

[2025-08-17 07:52:27] - Content Quality Gate Integration
**Decision:** Integrated content quality validation directly into Reader stage
**Rationale:** Prevent low-quality content from entering analysis pipeline, improving final report quality
**Implementation:** Added validate_content() call before document creation, tracks rejections in partial_failures
**Impact:** 2 pages rejected in testing (CNN.com, NBCNews.com), improved content standards

[2025-08-17 07:52:27] - Enhanced JSON Parsing Robustness
**Decision:** Implemented multi-stage JSON parsing with repair and fallback extraction
**Rationale:** LLM responses occasionally generate malformed JSON causing pipeline failures
**Implementation:** Added _repair_json() for common fixes, _extract_claims_fallback() for regex-based extraction
**Impact:** Successfully recovered 14 and 5 claims respectively during testing, zero pipeline failures

[2025-08-17 07:52:27] - Streamlit UI Progress Enhancement
**Decision:** Replaced static spinner with dynamic progress bars and real-time status updates
**Rationale:** Better user experience with visibility into pipeline progress and estimated completion time
**Implementation:** ProgressCallback class updates UI elements directly, throttled to 0.5s intervals
**Impact:** Users now see Planning (10%), Searching (25%), Reading (50%), Analyzing (70%), Verifying (85%), Writing (95%), Complete (100%)