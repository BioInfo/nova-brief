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

🤖 **OpenRouter Integration**
- Uses OpenRouter API with Cerebras provider pinning
- Model: `openai/gpt-oss-120b` for high-performance research
- Structured JSON outputs via JSON Schema validation

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

# Run evaluation harness
uv run python eval/harness.py

# Quick evaluation
uv run python eval/harness.py --quick --max-topics 3
```

## Configuration

Configure Nova Brief via environment variables in `.env`:

```bash
# Required
OPENROUTER_API_KEY=your_api_key_here

# Optional (with defaults)
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
MODEL="openai/gpt-oss-120b"
SEARCH_PROVIDER=duckduckgo
MAX_ROUNDS=3
PER_DOMAIN_CAP=3
FETCH_TIMEOUT_S=15
ENABLE_CACHE=false
LOG_LEVEL=INFO
USER_AGENT=NovaBrief-Research/0.1
```

### Advanced Settings

- **MAX_ROUNDS**: Number of iterative research rounds (1-5)
- **PER_DOMAIN_CAP**: Maximum results per domain (prevents over-reliance)
- **FETCH_TIMEOUT_S**: Timeout for web page fetching
- **Domain Filters**: Include/exclude specific domains in research

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │    │  Agent Pipeline │    │  OpenRouter API │
│                 │───▶│                 │───▶│                 │
│ • Topic Input   │    │ • Planner       │    │ • Cerebras      │
│ • Configuration │    │ • Searcher      │    │ • GPT-OSS-120B  │
│ • Progress      │    │ • Reader        │    │ • JSON Schema   │
│ • Results       │    │ • Analyst       │    │                 │
│                 │    │ • Verifier      │    │                 │
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
├── eval/                  # Evaluation harness
├── docs/                  # Documentation
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

**"OpenRouter API key required"**
- Ensure `OPENROUTER_API_KEY` is set in your `.env` file
- Verify the API key is valid at [openrouter.ai](https://openrouter.ai)

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

### Planned: Stage 2
- Async HTTP client with rate limiting
- SQLite caching layer
- Pydantic v2 data models
- Enhanced evaluation metrics

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

**Built with**: Python 3.9+, Streamlit, OpenRouter, Cerebras, DuckDuckGo