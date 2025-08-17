# Multi-Model Evaluation Harness Testing Guide

## Overview

The Nova Brief Multi-Model Evaluation Harness enables comparative performance analysis across multiple LLM models, providers, and routing configurations. This document provides comprehensive testing instructions, performance benchmarks, and usage guidelines.

## Table of Contents
- [System Architecture](#system-architecture)
- [Available Models](#available-models)
- [Comparison Sets](#comparison-sets)
- [Usage Instructions](#usage-instructions)
- [Test Results](#test-results)
- [Performance Metrics](#performance-metrics)
- [Command Reference](#command-reference)
- [Best Practices](#best-practices)

## System Architecture

### Components
- **MultiModelEvaluationHarness**: Core evaluation engine supporting 1-5 model comparisons
- **Comparative Analysis Engine**: Statistical analysis and ranking system
- **Results Management**: JSON output with detailed metrics and cross-model statistics
- **Convenience Scripts**: Shell wrapper for easier execution

### Key Features
- Simultaneous evaluation across multiple models
- Statistical analysis with means, standard deviations, and rankings
- Flexible model selection (predefined sets or custom combinations)
- Comprehensive performance metrics (speed, quality, reliability, verbosity)
- Backward compatibility with single-model evaluation

## Available Models

### Current Model Inventory
```
claude-sonnet-4-openrouter-default: Claude Sonnet 4 (OpenRouter Default)
claude-sonnet-4-direct: Claude Sonnet 4 (Direct Anthropic)
gemini-2.5-flash-openrouter-default: Gemini 2.5 Flash (OpenRouter Default)
gemini-2.5-flash-direct: Gemini 2.5 Flash (Direct Google)
gemini-2.5-pro-openrouter-default: Gemini 2.5 Pro (OpenRouter Default)
gemini-2.5-pro-direct: Gemini 2.5 Pro (Direct Google)
kimi-k2-openrouter-default: Kimi K2 (OpenRouter Default)
gpt-oss-120b-openrouter-default: GPT-OSS-120B (OpenRouter Default) 🧠
gpt-oss-120b-openrouter-cerebras: GPT-OSS-120B (OpenRouter + Cerebras) 🧠
gpt-5-mini-openrouter-default: GPT-5 Mini (OpenRouter Default)
gpt-5-mini-direct: GPT-5 Mini (Direct OpenAI)
qwen3-235b-openrouter-default: Qwen3-235B (OpenRouter Default)
```

### Model Categories
- **Large Models**: Claude Sonnet 4, Gemini 2.5 Pro, Qwen3-235B
- **Medium Models**: GPT-OSS-120B, Gemini 2.5 Flash
- **Small Models**: GPT-5 Mini, Kimi K2
- **Cerebras-Optimized**: GPT-OSS-120B variants with hardware acceleration

## Comparison Sets

### Default Set (Recommended for Most Testing)
```bash
Models: gpt-oss-120b-openrouter-cerebras, gpt-oss-120b-openrouter-default, claude-sonnet-4-openrouter-default
Purpose: Compare routing strategies and model capabilities
Duration: ~3-5 minutes per topic
```

### Quick Set (Fast A/B Testing)
```bash
Models: gpt-oss-120b-openrouter-cerebras, gpt-oss-120b-openrouter-default
Purpose: Compare Cerebras vs default routing for same model
Duration: ~2-3 minutes per topic
```

### Comprehensive Set (Full Analysis)
```bash
Models: gpt-oss-120b-openrouter-cerebras, gpt-oss-120b-openrouter-default, claude-sonnet-4-openrouter-default, gemini-2.5-flash-openrouter-default, gpt-5-mini-openrouter-default
Purpose: Cross-provider and cross-model performance analysis
Duration: ~8-12 minutes per topic
```

## Usage Instructions

### Direct Python Execution

#### List Available Models
```bash
uv run python eval/multi_model_harness.py --list-models
```

#### Run Default Comparison
```bash
uv run python eval/multi_model_harness.py --comparison-set default
```

#### Run Quick Comparison
```bash
uv run python eval/multi_model_harness.py --comparison-set quick --quick --max-topics 2
```

#### Custom Model Selection
```bash
uv run python eval/multi_model_harness.py --models gpt-oss-120b-openrouter-cerebras,claude-sonnet-4-openrouter-default,gpt-5-mini-openrouter-default
```

### Convenience Script Usage

#### Make Script Executable (One-time Setup)
```bash
chmod +x tools/scripts/run_model_comparison.sh
```

#### Basic Usage
```bash
# Default 3-model comparison
./tools/scripts/run_model_comparison.sh

# Quick 2-model comparison
./tools/scripts/run_model_comparison.sh --quick --topics 2

# Comprehensive 5-model comparison
./tools/scripts/run_model_comparison.sh --set comprehensive

# Custom model selection
./tools/scripts/run_model_comparison.sh --models gpt-oss-120b-openrouter-cerebras,claude-sonnet-4-openrouter-default
```

## Test Results

### Benchmark Test: AI Healthcare Impact (Single Topic)

#### Test Configuration
- **Topic**: "Impact of artificial intelligence on healthcare in 2024"
- **Mode**: Quick evaluation (1 round, 2 sources per domain, 10s timeout)
- **Expected Elements**: AI applications, current implementations, benefits/challenges, future prospects

#### Performance Results

| Model | Duration | Words | Sources | Coverage | Success Rate |
|-------|----------|-------|---------|----------|--------------|
| GPT-OSS-120B (Default) | 58.0s | 1,440 | 7 | 50.0% | 100% |
| GPT-OSS-120B (Cerebras) | 78.9s | 1,085 | 23 | 50.0% | 100% |

#### Comparative Rankings

**🚀 Speed (Fastest to Slowest)**
1. GPT-OSS-120B (Default): 58.0s
2. GPT-OSS-120B (Cerebras): 78.9s

**📝 Verbosity (Most to Least Words)**
1. GPT-OSS-120B (Default): 1,440 words
2. GPT-OSS-120B (Cerebras): 1,085 words

**📊 Research Depth (Most Sources)**
1. GPT-OSS-120B (Cerebras): 23 sources
2. GPT-OSS-120B (Default): 7 sources

#### Key Insights
- **Default Routing**: Faster execution, more verbose output, fewer sources
- **Cerebras Routing**: Slower but more thorough research, concise output
- **Trade-offs**: Speed vs research depth, verbosity vs source diversity

## Performance Metrics

### Primary Metrics

#### Speed Ranking
- **Measurement**: Average duration per topic (seconds)
- **Interpretation**: Lower is better for faster results
- **Use Case**: Time-sensitive evaluations, quick turnaround requirements

#### Quality Ranking  
- **Measurement**: Content coverage score (0.0-1.0)
- **Interpretation**: Higher is better for comprehensive coverage
- **Calculation**: Percentage of expected elements found in report content

#### Reliability Ranking
- **Measurement**: Success rate percentage (0-100%)
- **Interpretation**: Higher is better for consistent performance
- **Use Case**: Production deployment decisions

#### Verbosity Ranking
- **Measurement**: Average word count per report
- **Interpretation**: Context-dependent (verbose vs concise preferences)
- **Use Case**: Output length optimization

### Statistical Metrics

#### Variability Analysis
- **Standard Deviation**: Measures consistency across topics
- **Lower values**: More predictable performance
- **Higher values**: More variable results

#### Cross-Model Statistics
- **Comparative Rankings**: Relative performance across all metrics
- **Performance Profiles**: Strengths and weaknesses identification
- **Optimization Guidance**: Model selection recommendations

## Command Reference

### Core Arguments

```bash
--models MODEL1,MODEL2,...     # Custom model list (1-5 models)
--comparison-set SET           # Predefined set (default, quick, comprehensive)
--quick                        # Enable quick mode
--max-topics N                 # Limit evaluation to N topics
--topics-file PATH             # Custom topics file
--list-models                  # Show available models and sets
```

### Evaluation Modes

#### Standard Mode
- **Rounds**: 2
- **Sources per domain**: 3
- **Timeout**: 15 seconds
- **Use case**: Comprehensive evaluation

#### Quick Mode
- **Rounds**: 1
- **Sources per domain**: 2
- **Timeout**: 10 seconds
- **Use case**: Fast comparison, development testing

### Output Files

#### Result Files
- **Location**: `eval/multi_model_results_YYYYMMDD_HHMMSS.json`
- **Format**: Structured JSON with detailed metrics
- **Contents**: Model metrics, cross-model stats, detailed results

#### Topics File
- **Location**: `eval/topics.json` (auto-created if missing)
- **Format**: JSON array with topic definitions
- **Customization**: Modify for domain-specific evaluations

## Best Practices

### Model Selection Guidelines

#### For Development Testing
```bash
# Quick routing comparison
./tools/scripts/run_model_comparison.sh --set quick --quick --topics 1
```

#### For Production Evaluation
```bash
# Comprehensive analysis
./tools/scripts/run_model_comparison.sh --set default --topics 3
```

#### For Research Analysis
```bash
# Full model spectrum
./tools/scripts/run_model_comparison.sh --set comprehensive --topics 5
```

### Performance Optimization

#### Resource Management
- **API Rate Limits**: Stagger requests across different providers
- **Memory Usage**: Limit concurrent evaluations for large topic sets
- **Cost Control**: Use quick mode for iterative testing

#### Result Interpretation
- **Speed vs Quality**: Balance evaluation time against thoroughness
- **Provider Selection**: Consider cost, speed, and quality trade-offs
- **Routing Strategy**: Evaluate Cerebras vs default routing benefits

### Troubleshooting

#### Common Issues
```bash
# Missing API keys
Error: "Model validation failed: OPENROUTER_API_KEY: Missing API key"
Solution: Configure required API keys in .env file

# No topics found
Error: "No evaluation topics found"
Solution: Ensure eval/topics.json exists or will be auto-created

# Model not available
Error: "Unknown model: model-name"
Solution: Use --list-models to see available options
```

#### Environment Validation
```bash
# Check configuration
uv run python -c "from src.config import validate_environment; print(validate_environment())"

# Test single model
uv run python eval/harness.py --quick --max-topics 1
```

### Advanced Usage

#### Custom Topics
```json
{
  "description": "Custom evaluation topics",
  "version": "1.0",
  "topics": [
    {
      "topic": "Your research topic here",
      "expected_elements": [
        "Element 1",
        "Element 2",
        "Element 3"
      ]
    }
  ]
}
```

#### Batch Evaluation Scripts
```bash
#!/bin/bash
# Multiple comparison sets
for set in quick default comprehensive; do
    echo "Running $set comparison..."
    ./tools/scripts/run_model_comparison.sh --set $set --quick --topics 2
done
```

## Conclusion

The Multi-Model Evaluation Harness provides a robust framework for comparing LLM performance across different models, providers, and routing strategies. Use the guidelines in this document to conduct meaningful evaluations that inform model selection and optimization decisions for your specific use cases.

For additional support or feature requests, refer to the main project documentation or create an issue in the project repository.