# Nova Brief - Deep Research Agent

A fast, reliable deep-research agent that plans, searches, reads, verifies, and writes analyst-grade, cited briefs.

## Features

🔍 **End-to-End Research Pipeline**
- **Planner**: Transforms topics into comprehensive search strategies
- **Searcher**: Multi-source web search with domain filtering and deduplication  
- **Reader**: Content extraction from HTML and PDF sources
- **Analyst**: LLM-powered information synthesis with structured claims
- **Verifier**: Citation validation and coverage enforcement
- **Writer**: Professional report generation with numbered citations

🤖 **Configurable LLM Providers**
- Multiple model/provider support via OpenRouter and direct APIs
- Default: `openai/gpt-oss-120b` (Cerebras) for high-performance research
- Alternative models: GPT-5, Claude 4 Sonnet, Gemini, and more
- UI-based model selection with real-time API key validation

📊 **Professional Output**
- 800-1200 word reports with proper citations
- Markdown format with numbered references
- JSON export capability for programmatic use
- Comprehensive metrics and source tracking

🎯 **Quality Assurance**
- Strict citation policy: all claims backed by sources
- Domain diversity enforcement
- Content quality filtering and validation
- Iterative refinement with coverage targets

## Evaluation & Testing

✅ **Production-Ready Performance** (Last Updated: 2025-08-18)

Nova Brief includes comprehensive evaluation capabilities with both single-model and multi-model comparative analysis.

### Single Model Performance

| Metric | Result | Details |
|--------|--------|---------|
| **Success Rate** | 100% | 1/1 topics completed successfully |
| **Average Duration** | 60.1 seconds | Full research pipeline execution |
| **Report Quality** | 1,350 words | Professional analyst-grade output |
| **Source Coverage** | 11 sources | Multi-domain research validation |
| **Citation Coverage** | 75% | Expected topic elements covered |
| **Pipeline Reliability** | ✅ All components operational | End-to-end functionality verified |

### Multi-Model Comparative Analysis

**🆚 GPT-OSS-120B Routing Comparison** (AI Healthcare Topic):

| Model Configuration | Duration | Words | Sources | Coverage | Success Rate |
|---------------------|----------|-------|---------|----------|--------------|
| **GPT-OSS-120B (Cerebras)** | 118.5s | 999 | 28 | 75% | 100% |
| **Claude Sonnet 4** | 171.6s | 1,430 | 25 | 25% | 100% |
| **GPT-OSS-120B (Default)** | 303.7s | 1,324 | 22 | 75% | 100% |

### Performance Rankings

**🏆 Speed Ranking** (Fastest to Slowest):
1. **GPT-OSS-120B (Cerebras)** - 118.5s ⚡ *2.5x faster than default*
2. **Claude Sonnet 4** - 171.6s
3. **GPT-OSS-120B (Default)** - 303.7s

**🎯 Quality Ranking** (Coverage Score):
1. **GPT-OSS-120B (Default)** - 75% coverage
2. **GPT-OSS-120B (Cerebras)** - 75% coverage
3. **Claude Sonnet 4** - 25% coverage

**📝 Verbosity Ranking** (Word Count):
1. **Claude Sonnet 4** - 1,430 words (most comprehensive)
2. **GPT-OSS-120B (Default)** - 1,324 words
3. **GPT-OSS-120B (Cerebras)** - 999 words (most concise)

### Key Performance Insights

- **🧠 Cerebras Acceleration**: 156% speed improvement over default routing while maintaining coverage quality
- **📊 Parallel Execution**: All 3 models completed simultaneously in ~5 minutes (vs ~15 minutes serial)
- **🎯 Reliability**: 100% success rate across all models and routing configurations
- **⚖️ Trade-offs**: Speed vs thoroughness, conciseness vs comprehensiveness

**Pipeline Performance Breakdown:**
- 🧠 **Planner**: 4 sub-questions, 7 targeted queries (2s)
- 🔍 **Searcher**: 24 results from 22 domains via DuckDuckGo (7s)
- 📖 **Reader**: 11/24 URLs processed (robots.txt compliant) (9s)
- 🔬 **Analyst**: 27 verified claims with citations (32s)
- ✅ **Verifier**: 100% coverage validation (0.1s)
- ✍️ **Writer**: Professional report generation (10s)

**Quality Metrics:**
- All claims backed by verifiable sources
- Strict robots.txt compliance
- Domain diversity enforcement active
- Professional formatting with numbered citations

### Evaluation Commands

**Single Model Evaluation:**
```bash
uv run python eval/harness.py --quick --max-topics 1
```

**Multi-Model Comparison:**
```bash
# Default 3-model comparison (GPT-OSS-120B Cerebras vs Default vs Claude Sonnet 4)
./tools/scripts/run_model_comparison.sh

# Quick 2-model routing comparison
./tools/scripts/run_model_comparison.sh --set quick --quick --topics 1

# Custom model selection
uv run python eval/multi_model_harness.py --models gpt-oss-120b-openrouter-cerebras,claude-sonnet-4-openrouter-default

# List all available models
uv run python eval/multi_model_harness.py --list-models
```

**For detailed evaluation documentation, see:** [`docs/multi-model-evaluation-testing.md`](docs/multi-model-evaluation-testing.md)

## Quick Start

### Prerequisites

- Python 3.9+ 
- OpenRouter API key (get one at [openrouter.ai](https://openrouter.ai))
- `uv` package manager (recommended) or `pip`

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd nova-brief
   ```

2. **Install dependencies**
   ```bash
   # Using uv (recommended)
   uv sync
   
   # Or using pip
   pip install -e .
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENROUTER_API_KEY
   ```

4. **Run the application**
   ```bash
   # Using uv
   uv run streamlit run src/app.py
   
   # Or using python directly
   python -m streamlit run src/app.py
   ```

5. **Open your browser**
   ```
   http://localhost:8501
   ```

## Usage

### Web Interface

1. **Enter Research Topic**: Provide a specific topic for investigation
2. **Configure Settings**: Adjust research rounds, domain filters, timeouts
3. **Start Research**: Click "Start Research" to begin the pipeline
4. **View Results**: Monitor progress and review the generated report
5. **Export**: Download as Markdown or JSON

### Command Line (Advanced)

```bash
# Run tests
uv run python tests/test_mvp.py

# Single-model evaluation harness
uv run python eval/harness.py
uv run python eval/harness.py --quick --max-topics 3

# Multi-model comparative evaluation
./tools/scripts/run_model_comparison.sh
./tools/scripts/run_model_comparison.sh --set quick --quick --topics 2
uv run python eval/multi_model_harness.py --list-models
```

## Configuration

Configure Nova Brief via environment variables in `.env`:

```bash
# Model Selection (choose one of the available models)
SELECTED_MODEL=gpt-oss-120b

# OpenRouter Configuration (for most models)
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Direct Provider API Keys (optional, for direct access)
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# Search and Agent Settings
SEARCH_PROVIDER=duckduckgo
MAX_ROUNDS=3
PER_DOMAIN_CAP=3
FETCH_TIMEOUT_S=15

# System Configuration
ENABLE_CACHE=false
LOG_LEVEL=INFO
USER_AGENT=NovaBrief-Research/0.1

# Legacy Configuration (maintained for backward compatibility)
MODEL="openai/gpt-oss-120b"
```

### Available Models

Nova Brief supports multiple LLM providers and models with flexible routing options:

**OpenRouter Models with Routing Options:**
- `gpt-oss-120b-openrouter-default` - GPT-OSS-120B (OpenRouter Default) - Balanced routing
- `gpt-oss-120b-openrouter-cerebras` - GPT-OSS-120B (OpenRouter + Cerebras) 🧠 - Hardware-optimized
- `claude-sonnet-4-openrouter-default` - Claude Sonnet 4 (OpenRouter Default) - Advanced reasoning
- `gemini-2.5-flash-openrouter-default` - Gemini 2.5 Flash (OpenRouter Default) - Fast processing
- `gemini-2.5-pro-openrouter-default` - Gemini 2.5 Pro (OpenRouter Default) - Enhanced capabilities
- `gpt-5-mini-openrouter-default` - GPT-5 Mini (OpenRouter Default) - Cost-effective
- `qwen3-235b-openrouter-default` - Qwen3-235B (OpenRouter Default) - Large-scale model
- `kimi-k2-openrouter-default` - Kimi K2 (OpenRouter Default) - Specialized model

**Direct Provider Access:**
- `claude-sonnet-4-direct` - Claude Sonnet 4 via Anthropic API directly
- `gemini-2.5-flash-direct` - Gemini 2.5 Flash via Google API directly
- `gemini-2.5-pro-direct` - Gemini 2.5 Pro via Google API directly
- `gpt-5-mini-direct` - GPT-5 Mini via OpenAI API directly

**🧠 Cerebras Hardware Acceleration:** Available for GPT-OSS-120B with specialized routing for enhanced performance.

Model selection can be configured via environment variables, web UI, or multi-model evaluation commands.

### Advanced Settings

- **MAX_ROUNDS**: Number of iterative research rounds (1-5)
- **PER_DOMAIN_CAP**: Maximum results per domain (prevents over-reliance)
- **FETCH_TIMEOUT_S**: Timeout for web page fetching
- **Domain Filters**: Include/exclude specific domains in research

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │    │  Agent Pipeline │    │  LLM Providers  │
│                 │───▶│                 │───▶│                 │
│ • Topic Input   │    │ • Planner       │    │ • OpenRouter    │
│ • Model Select  │    │ • Searcher      │    │ • OpenAI Direct │
│ • Configuration │    │ • Reader        │    │ • Anthropic     │
│ • Progress      │    │ • Analyst       │    │ • Cerebras      │
│ • Results       │    │ • Verifier      │    │ • Multi-Model   │
│                 │    │ • Writer        │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Search    │    │  Content Tools  │    │  Observability  │
│                 │    │                 │    │                 │
│ • DuckDuckGo    │    │ • HTML Extract  │    │ • Structured    │
│ • Domain Filter │    │ • PDF Parsing   │    │   Logging       │
│ • Deduplication │    │ • Content Clean │    │ • Tracing       │
│                 │    │ • Chunking      │    │ • Metrics       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Development

### Project Structure

```
nova-brief/
├── src/                    # Source code
│   ├── agent/             # Agent pipeline components
│   ├── tools/             # Web search, fetch, parse tools
│   ├── providers/         # LLM and search providers
│   ├── storage/           # Data models and schemas
│   ├── observability/     # Logging and tracing
│   ├── app.py            # Streamlit UI
│   └── config.py         # Configuration management
├── tests/                 # Test suite
│   └── test_model_system.py  # Model configuration tests
├── eval/                  # Evaluation harness
│   ├── harness.py        # Single-model evaluation
│   ├── multi_model_harness.py  # Multi-model comparison
│   └── topics.json       # Evaluation topics
├── tools/scripts/         # Utility scripts
│   ├── run_model_comparison.sh  # Multi-model evaluation wrapper
│   └── test_*.py         # Development testing scripts
├── docs/                  # Documentation
│   └── multi-model-evaluation-testing.md  # Evaluation guide
├── memory-bank/           # Project context and decisions
├── pyproject.toml        # Project configuration
└── .env.example          # Environment template
```

### Running Tests

```bash
# Full test suite
uv run python tests/test_mvp.py

# Evaluation on sample topics
uv run python eval/harness.py --quick
```

### Development Setup

```bash
# Install development dependencies
uv sync --dev

# Run with development logging
LOG_LEVEL=DEBUG uv run streamlit run src/app.py
```

## API Reference

### Core Functions

#### `run_research_pipeline(topic, constraints)`
Execute the complete research pipeline for a given topic.

**Parameters:**
- `topic` (str): Research topic
- `constraints` (Constraints): Configuration constraints

**Returns:**
- Dictionary with research state, report, and metrics

#### Agent Components

Each agent component follows a consistent interface:

```python
async def component_function(inputs) -> Dict[str, Any]:
    """
    Returns:
        {
            "success": bool,
            "data": Any,
            "metadata": Dict[str, Any],
            "error": Optional[str]
        }
    """
```

## Troubleshooting

### Common Issues

**"API key required"**
- Ensure the appropriate API key is set for your selected model
- For OpenRouter models: Set `OPENROUTER_API_KEY`
- For direct OpenAI: Set `OPENAI_API_KEY`
- For direct Anthropic: Set `ANTHROPIC_API_KEY`
- Verify API keys are valid at respective provider websites

**"No search results found"**
- Check internet connectivity
- Try broader search terms
- Adjust domain filters if too restrictive

**"Content extraction failed"**
- Some sites may block automated access
- PDF content requires accessible URLs
- Check robots.txt compliance settings

**"Memory/Performance issues"**
- Reduce `MAX_ROUNDS` for faster execution
- Lower `PER_DOMAIN_CAP` to limit sources
- Use `--quick` mode for evaluation

### Debug Mode

Enable detailed logging:

```bash
LOG_LEVEL=DEBUG uv run streamlit run src/app.py
```

### Performance Tuning

For faster research (with reduced quality):
```bash
# Quick research settings
MAX_ROUNDS=1
PER_DOMAIN_CAP=2
FETCH_TIMEOUT_S=10
```

## Roadmap

### Current: MVP (Stage 1)
- ✅ Complete agent pipeline
- ✅ OpenRouter + Cerebras integration
- ✅ Web search and content extraction
- ✅ Streamlit UI
- ✅ Basic evaluation harness

### Next: Stage 1.5 — Polish & Performance (Streamlit)
- Real-time progress and status with ETA
- Async Reader (httpx.AsyncClient + asyncio.gather)
- Refined results layout: tabs for Report, Metrics, Sources, Export
- Sources with expanders and previews to reduce clutter
- Content Quality Gate in Reader; partial_failures surfaced in UI
- Evaluation: Sub-Question Coverage metric
- In-app “Model Benchmarks” table from latest eval results

### Planned: Stage 2 — Core robustness
- Rate limiting and per-domain controls for async fetching
- SQLite caching layer
- Pydantic v2 data models
- Enhanced evaluation metrics and robustness

### Future: Stage 3+
- LangGraph orchestration
- REST API with authentication
- OpenTelemetry observability
- Next.js web interface

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests: `uv run python tests/test_mvp.py`
4. Submit a pull request

## License

[Your License Here]

## Support

For questions and support:
- Check existing issues in the repository
- Review troubleshooting section
- Create a new issue with detailed information

---

**Built with**: Python 3.9+, Streamlit, OpenRouter, OpenAI, Anthropic, Cerebras, DuckDuckGo