#!/bin/bash
# Convenient script to run multi-model comparisons for Nova Brief

set -e

# Default values
COMPARISON_SET="default"
QUICK_MODE=""
MAX_TOPICS=""
MODELS=""

# Help function
show_help() {
    echo "Nova Brief Multi-Model Comparison Runner"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -s, --set SETNAME       Use predefined comparison set (default, quick, comprehensive)"
    echo "  -m, --models MODEL1,MODEL2  Custom model list (comma-separated, 1-5 models)"
    echo "  -q, --quick             Enable quick mode (faster evaluation)"
    echo "  -t, --topics N          Limit to N topics (default: all topics)"
    echo "  -l, --list              List available models and comparison sets"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run default 3-model comparison"
    echo "  $0 --quick --topics 2                # Quick comparison on 2 topics"
    echo "  $0 --set comprehensive               # Run 5-model comprehensive comparison"
    echo "  $0 --models gpt-oss-120b-openrouter-cerebras,claude-sonnet-4-openrouter-default"
    echo "  $0 --list                            # Show available models"
    echo ""
    echo "Default comparison set includes:"
    echo "  - GPT-OSS-120B (OpenRouter + Cerebras)"
    echo "  - GPT-OSS-120B (OpenRouter Default)"  
    echo "  - Claude Sonnet 4 (OpenRouter Default)"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--set)
            COMPARISON_SET="$2"
            shift 2
            ;;
        -m|--models)
            MODELS="$2"
            shift 2
            ;;
        -q|--quick)
            QUICK_MODE="--quick"
            shift
            ;;
        -t|--topics)
            MAX_TOPICS="--max-topics $2"
            shift 2
            ;;
        -l|--list)
            echo "Listing available models and comparison sets..."
            uv run python eval/multi_model_harness.py --list-models
            exit 0
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Build command
CMD="uv run python eval/multi_model_harness.py"

if [[ -n "$MODELS" ]]; then
    # Convert comma-separated models to space-separated for --models argument
    MODELS_ARGS=$(echo "$MODELS" | tr ',' ' ')
    CMD="$CMD --models $MODELS_ARGS"
else
    CMD="$CMD --comparison-set $COMPARISON_SET"
fi

if [[ -n "$QUICK_MODE" ]]; then
    CMD="$CMD $QUICK_MODE"
fi

if [[ -n "$MAX_TOPICS" ]]; then
    CMD="$CMD $MAX_TOPICS"
fi

echo "🚀 Running Nova Brief Multi-Model Comparison..."
echo "Command: $CMD"
echo ""

# Execute the command
eval $CMD