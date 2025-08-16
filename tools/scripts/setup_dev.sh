#!/bin/bash
# Development environment setup script for Nova Brief

set -e

echo "🔬 Nova Brief Development Setup"
echo "================================"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ uv found"

# Create virtual environment
echo "📦 Creating virtual environment..."
uv venv

# Activate environment and install dependencies
echo "📥 Installing dependencies..."
uv pip install -e ".[dev]"

# Copy environment template if .env doesn't exist
if [ ! -f .env ]; then
    echo "⚙️  Creating .env file from template..."
    cp .env.example .env
    echo "🔧 Please edit .env file and add your API keys"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys:"
echo "   nano .env"
echo ""
echo "2. Activate the environment:"
echo "   source .venv/bin/activate"
echo ""
echo "3. Run the application:"
echo "   uv run streamlit run src/app.py"
echo ""
echo "4. Run tests:"
echo "   uv run python tests/test_mvp.py"
echo ""
echo "5. Run evaluation:"
echo "   uv run python eval/harness.py --quick"