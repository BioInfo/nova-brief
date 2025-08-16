# 🧠 Nova Brief

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![GitHub stars](https://img.shields.io/github/stars/BioInfo/nova-brief.svg?style=social&label=Star)](https://github.com/BioInfo/nova-brief)
[![GitHub forks](https://img.shields.io/github/forks/BioInfo/nova-brief.svg?style=social&label=Fork)](https://github.com/BioInfo/nova-brief/fork)
[![GitHub issues](https://img.shields.io/github/issues/BioInfo/nova-brief.svg)](https://github.com/BioInfo/nova-brief/issues)
[![GitHub last commit](https://img.shields.io/github/last-commit/BioInfo/nova-brief.svg)](https://github.com/BioInfo/nova-brief/commits/main)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](https://github.com/BioInfo/nova-brief/issues)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> **⚡ Fast, reliable deep-research agent powered by Cerebras GPT-OSS-120B**  
> Plans → Searches → Reads → Verifies → Writes analyst-grade cited briefs

<div align="center">

![Nova Brief Demo](https://via.placeholder.com/800x400/1a1a1a/ffffff?text=🚀+Demo+Coming+Soon)

</div>

---

## 🌟 Why Nova Brief?

| Feature | Traditional Research | 🧠 Nova Brief |
|---------|---------------------|---------------|
| **Speed** | Hours of manual work | ⚡ 60-90 seconds |
| **Sources** | Cherry-picked | 🔍 Multi-source verification |
| **Citations** | Manual formatting | 📝 Auto-generated with links |
| **Coverage** | Partial | ✅ Claim→source validation |
| **Bias** | Human limitations | 🤖 Systematic approach |

## 🚀 Key Features

- **🏃‍♂️ Blazing Fast**: ~3,000 tokens/sec on Cerebras infrastructure
- **📚 Analyst-Grade**: 800-1,200 word briefs with numbered citations
- **🔍 Source Verification**: Zero orphan claims policy
- **🌐 Multi-Provider**: DuckDuckGo, Tavily, Bing, Brave search support
- **🧠 Smart Planning**: Breaks topics into sub-questions for comprehensive coverage
- **📊 Cost Transparent**: Token tracking and spend estimation
- **🛡️ Compliant**: Respects robots.txt, rate limits, and privacy
- **📈 Scalable**: From MVP to production with observability built-in

## 🎯 Perfect For

- **📊 Analysts & PMs**: Fast first-pass research with credible sources
- **🔬 Engineers & Scientists**: Technical overviews with primary papers
- **👔 Executives**: One-screen briefs with risks, numbers, and sources

## ⚡ Quick Start

```bash
# Clone the repository
git clone https://github.com/BioInfo/nova-brief.git
cd nova-brief

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your CEREBRAS_API_KEY

# Launch the Streamlit app
streamlit run src/app.py
```

## 🏗️ Architecture

```
📝 Topic Input → 🧠 Planner → 🔍 Searcher → 📖 Reader → 🔬 Analyst → ✅ Verifier → ✍️ Writer → 📄 Report
                     ↓
              🚀 Cerebras GPT-OSS-120B
                     ↓
            🌐 Web Search + PDF Extract
```

<details>
<summary>🔍 <strong>Detailed Flow</strong></summary>

1. **🧠 Planner**: Breaks topic into sub-questions and search queries
2. **🔍 Searcher**: Multi-provider search with domain caps and deduplication  
3. **📖 Reader**: Fetches pages, extracts content, respects robots.txt
4. **🔬 Analyst**: Synthesizes claims with source tracking
5. **✅ Verifier**: Enforces coverage policy, triggers follow-ups
6. **✍️ Writer**: Generates final Markdown with numbered citations

</details>

## 📦 Staged Rollout

### 🎯 Stage 1 - MVP (Current)
- [x] Python + Streamlit UI
- [x] Cerebras integration via OpenAI-compatible API
- [x] Basic agent loop with claim verification
- [x] Web search + PDF parsing
- [x] Markdown output with citations

### 🚀 Stage 2 - Robustness
- [ ] Async I/O with per-domain rate limits
- [ ] SQLite caching and deduplication
- [ ] Pydantic v2 schemas and JSON export
- [ ] Evaluation harness with 10 test topics

### ⚙️ Stage 3 - Scale & Control
- [ ] LangGraph orchestration
- [ ] REST API with authentication  
- [ ] Project workspaces and source controls
- [ ] OpenTelemetry observability

### 🎨 Stage 4 - Production Polish
- [ ] Next.js web app with live traces
- [ ] Evidence map visualization
- [ ] Parallel processing for <90s completion
- [ ] Admin dashboard and usage analytics

## 📊 Performance Targets

| Metric | MVP (Stage 1) | Target (Stage 4) |
|--------|---------------|------------------|
| **Latency** | ≤6 minutes | 60-90 seconds |
| **Sources** | ≥5 per brief | ≥9 with diversity |
| **Coverage** | 100% claim→source | ≥90% with ≥2 sources |
| **Dead Links** | <10% | <5% |

## 🛠️ Development

```bash
# Development setup
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Run evaluation harness
python eval/harness.py

# View documentation
open docs/master-plan.md
```

## 📚 Documentation

- [📋 Product Requirements](docs/prd.md)
- [🗺️ Master Plan](docs/master-plan.md)
- [🏗️ Architecture Specs](docs/specs/)
- [🧠 Memory Bank](memory-bank/)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### 🐛 Found a Bug?
[Open an issue](https://github.com/BioInfo/nova-brief/issues/new) with detailed reproduction steps.

### 💡 Have an Idea?
[Start a discussion](https://github.com/BioInfo/nova-brief/discussions) to share your thoughts!

## 📈 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=BioInfo/nova-brief&type=Date)](https://star-history.com/#BioInfo/nova-brief&Date)

## 🎉 Community

<div align="center">

[![GitHub followers](https://img.shields.io/github/followers/BioInfo?style=social)](https://github.com/BioInfo)
[![Twitter Follow](https://img.shields.io/twitter/follow/novabrief?style=social)](https://twitter.com/novabrief)

**Join the conversation!** 💬

[🐛 Issues](https://github.com/BioInfo/nova-brief/issues) • 
[💡 Discussions](https://github.com/BioInfo/nova-brief/discussions) • 
[📧 Contact](mailto:hello@novabrief.ai)

</div>

## 🙏 Acknowledgments

- **🧠 Cerebras**: For the blazing-fast GPT-OSS-120B inference
- **🌐 OpenAI**: For the compatible API standard
- **🔍 Search Providers**: DuckDuckGo, Tavily, and others
- **🐍 Python Community**: For the amazing ecosystem

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**⭐ Star this repo if you find it helpful!** ⭐

[![GitHub stars](https://img.shields.io/github/stars/BioInfo/nova-brief.svg?style=social&label=Star&maxAge=2592000)](https://github.com/BioInfo/nova-brief/stargazers)

*Made with ❤️ by the Nova Brief team*

</div>