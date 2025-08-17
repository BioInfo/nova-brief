"""Streamlit UI for Nova Brief research agent."""

import os
import asyncio
import time
from typing import Dict, Any, Optional
import streamlit as st
from datetime import datetime
import json
from dotenv import load_dotenv
import glob

# Load environment variables first
load_dotenv()

# Import agent components
from src.agent.orchestrator import run_research_pipeline, validate_pipeline_inputs
from src.storage.models import create_default_constraints, Constraints
from src.config import Config
from src.observability.logging import get_logger
from src.tools.eta import estimate_eta, format_eta, get_latest_eval_results

# Configure logging
logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="Nova Brief - Research Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
def init_session_state():
    """Initialize Streamlit session state variables."""
    if 'research_results' not in st.session_state:
        st.session_state.research_results = None
    if 'research_running' not in st.session_state:
        st.session_state.research_running = False
    if 'research_logs' not in st.session_state:
        st.session_state.research_logs = []
    # Stage 1.5: Progress tracking
    if 'research_state' not in st.session_state:
        st.session_state.research_state = None
    if 'research_start_time' not in st.session_state:
        st.session_state.research_start_time = None


def main():
    """Main Streamlit application."""
    init_session_state()
    
    # Header
    st.title("🔍 Nova Brief")
    st.markdown("**Deep Research Agent** - Generate analyst-grade briefs with citations")
    
    # Check environment setup
    if not _check_environment():
        st.error("⚠️ Environment not properly configured. Please set required API keys.")
        st.stop()
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Model selection
        selected_model = _render_model_selection()
        
        # Research constraints
        constraints = _render_constraints_form()
        
        # API Configuration status
        st.subheader("🔑 API Status")
        _render_api_status(selected_model)
        
        # Stage 1.5: Model Benchmarks
        st.subheader("📊 Model Benchmarks")
        _render_model_benchmarks()
        
        # About section
        st.subheader("ℹ️ About")
        st.markdown("""
        Nova Brief is a deep research agent that:
        - Plans comprehensive research queries
        - Searches multiple sources
        - Extracts and analyzes content
        - Verifies citations
        - Generates professional reports
        """)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("🎯 Research Topic")
        
        # Topic input
        topic = st.text_area(
            "Enter your research topic:",
            placeholder="e.g., Impact of artificial intelligence on healthcare in 2024",
            height=100,
            help="Provide a specific topic for comprehensive research"
        )
        
        # Validation
        if topic:
            validation = validate_pipeline_inputs(topic, constraints)
            if not validation["valid"]:
                for issue in validation["issues"]:
                    st.error(f"❌ {issue}")
        
        # Research button
        col_btn1, col_btn2 = st.columns([1, 2])
        
        with col_btn1:
            if st.button(
                "🚀 Start Research",
                disabled=not topic or st.session_state.research_running,
                type="primary"
            ):
                if topic and not st.session_state.research_running:
                    _run_research(topic, constraints, selected_model)
        
        with col_btn2:
            if st.session_state.research_running:
                st.warning("🔄 Research in progress...")
    
    with col2:
        st.header("📊 Status")
        _render_status_panel()
    
    # Results section
    if st.session_state.research_results:
        _render_results_section()
    
    # Logs section (expandable)
    with st.expander("📝 Research Logs", expanded=False):
        _render_logs_section()


def _check_environment() -> bool:
    """Check if required environment variables are set."""
    required_vars = ["OPENROUTER_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        st.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        st.markdown("""
        **Setup Instructions:**
        1. Copy `.env.example` to `.env`
        2. Set your `OPENROUTER_API_KEY`
        3. Restart the application
        """)
        return False
    
    return True


def _render_model_selection() -> str:
    """Render enhanced model selection UI component."""
    st.subheader("🤖 Model Selection")
    
    # Get available models and organize by base model
    available_models_dict = Config.get_available_models_dict()
    current_selection = Config.SELECTED_MODEL
    
    # Organize models by base model for better UI
    model_groups = {}
    for base_model_key in Config.BASE_MODELS.keys():
        base_config = Config.BASE_MODELS[base_model_key]
        model_groups[base_model_key] = {
            'name': base_config['name'],
            'variants': Config.get_models_by_base_model(base_model_key),
            'supports_cerebras': base_config['supports_cerebras']
        }
    
    # Create organized display options
    model_options = {}
    option_groups = []
    
    for base_key, group_info in model_groups.items():
        group_name = f"📱 {group_info['name']}"
        if group_info['supports_cerebras']:
            group_name += " 🧠"
        
        option_groups.append(f"--- {group_name} ---")
        model_options[f"--- {group_name} ---"] = None  # Separator
        
        for variant_key, model_config in group_info['variants'].items():
            # Add API key status indicator
            api_key = os.getenv(model_config.api_key_env)
            status = "✅" if api_key else "❌"
            
            # Create descriptive display name
            provider_info = model_config.provider.title()
            if model_config.provider_params:
                if "cerebras" in str(model_config.provider_params):
                    provider_info += " + Cerebras 🧠"
                else:
                    provider_info += f" + {model_config.provider_params}"
            elif model_config.provider == "openrouter":
                provider_info += " (Default)"
            else:
                provider_info = f"Direct {provider_info}"
            
            display_name = f"{status} {group_info['name']} ({provider_info})"
            model_options[display_name] = variant_key
    
    # Find current selection index
    current_index = 0
    try:
        current_display = next(k for k, v in model_options.items() if v == current_selection)
        current_index = list(model_options.keys()).index(current_display)
    except (StopIteration, ValueError):
        # Fallback to first non-separator option
        for i, (display, key) in enumerate(model_options.items()):
            if key is not None:
                current_index = i
                break
    
    # Selection widget with organized options
    selected_display = st.selectbox(
        "Choose Model Configuration:",
        options=list(model_options.keys()),
        index=current_index,
        help="Select model, provider, and inference method",
        format_func=lambda x: x if not x.startswith("---") else x  # Keep separator formatting
    )
    
    selected_model = model_options[selected_display]
    
    # Handle separator selection (shouldn't happen but be safe)
    if selected_model is None:
        # Find next valid option
        for display, key in model_options.items():
            if key is not None:
                selected_model = key
                break
    
    # Update session state if changed
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = selected_model
    elif st.session_state.selected_model != selected_model:
        st.session_state.selected_model = selected_model
        st.rerun()  # Refresh to update API status
    
    # Show selection breakdown
    if selected_model and selected_model in available_models_dict:
        model_config = available_models_dict[selected_model]
        
        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"🤖 **Model:** {model_config.model_id}")
            st.caption(f"🏢 **Provider:** {model_config.provider.title()}")
        with col2:
            if model_config.provider_params:
                st.caption(f"⚙️ **Inference:** {model_config.provider_params}")
            else:
                st.caption(f"⚙️ **Inference:** Default routing")
            if model_config.supports_cerebras:
                st.caption("🧠 **Cerebras:** Available")
    
    return selected_model


def _render_constraints_form() -> Constraints:
    """Render research constraints configuration form."""
    st.subheader("🎛️ Research Settings")
    
    # Load defaults
    defaults = create_default_constraints()
    
    # Max rounds
    max_rounds = st.slider(
        "Max Research Rounds",
        min_value=1,
        max_value=5,
        value=defaults["max_rounds"],
        help="Number of iterative research rounds"
    )
    
    # Per-domain cap
    per_domain_cap = st.slider(
        "Results per Domain",
        min_value=1,
        max_value=10,
        value=defaults["per_domain_cap"],
        help="Maximum results from each domain"
    )
    
    # Timeout
    fetch_timeout = st.slider(
        "Fetch Timeout (seconds)",
        min_value=5,
        max_value=30,
        value=int(defaults["fetch_timeout_s"]),
        help="Timeout for fetching web pages"
    )
    
    # Domain filters
    st.subheader("🌐 Domain Filters")
    
    include_domains_text = st.text_area(
        "Include Domains (one per line)",
        placeholder="edu\ngov\norg",
        height=80,
        help="Prioritize these domains in search results"
    )
    
    exclude_domains_text = st.text_area(
        "Exclude Domains (one per line)",
        placeholder="example.com\nspam-site.net",
        height=80,
        help="Exclude these domains from results"
    )
    
    # Parse domain filters
    include_domains = [d.strip() for d in include_domains_text.split('\n') if d.strip()]
    exclude_domains = [d.strip() for d in exclude_domains_text.split('\n') if d.strip()]
    
    # Create constraints object
    constraints: Constraints = {
        "date_range": None,
        "include_domains": include_domains,
        "exclude_domains": exclude_domains,
        "max_rounds": max_rounds,
        "per_domain_cap": per_domain_cap,
        "fetch_timeout_s": float(fetch_timeout),
        "max_tokens_per_chunk": 1000
    }
    
    return constraints


def _render_api_status(selected_model: str):
    """Render enhanced API configuration status for the selected model."""
    available_models = Config.get_available_models_dict()
    model_config = available_models.get(selected_model)
    
    if not model_config:
        st.error("❌ Invalid model configuration")
        return
    
    # API Key Status
    api_key = os.getenv(model_config.api_key_env)
    
    if api_key:
        st.success(f"✅ {model_config.api_key_env}")
        # Show partial key for verification
        masked_key = f"{api_key[:8]}...{api_key[-4:]}"
        st.code(masked_key)
    else:
        st.error(f"❌ {model_config.api_key_env} Missing")
        st.warning(f"Set {model_config.api_key_env} in your .env file")
        
        # Show required API key information
        if model_config.provider == "google":
            st.info("💡 Get Google AI API key: https://aistudio.google.com/app/apikey")
        elif model_config.provider == "anthropic":
            st.info("💡 Get Anthropic API key: https://console.anthropic.com/")
        elif model_config.provider == "openai":
            st.info("💡 Get OpenAI API key: https://platform.openai.com/api-keys")
        elif model_config.provider == "openrouter":
            st.info("💡 Get OpenRouter API key: https://openrouter.ai/keys")
    
    # Configuration Details
    st.info(f"🤖 Model: {model_config.model_id}")
    st.info(f"🏢 Provider: {model_config.provider.title()}")
    
    if model_config.provider_params:
        st.info(f"⚙️ Inference: {model_config.provider_params}")
    else:
        st.info(f"⚙️ Inference: Default routing")
    
    if model_config.base_url:
        st.info(f"🔗 Base URL: {model_config.base_url}")
    
    if model_config.supports_cerebras:
        st.info("🧠 Cerebras inference supported")


def _render_model_benchmarks():
    """Render model benchmarks section (Stage 1.5)."""
    try:
        # Get latest evaluation results
        eval_results = get_latest_eval_results()
        
        if not eval_results:
            st.info("💡 No benchmark data available. Run evaluation to see performance metrics.")
            st.code("uv run python eval/harness.py --quick --max-topics 1")
            return
        
        # Display benchmark summary
        if "avg_duration_s" in eval_results:
            # Single summary format
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Avg Duration", f"{eval_results.get('avg_duration_s', 0):.1f}s")
                st.metric("Success Rate", f"{eval_results.get('success_rate', 0):.0f}%")
            with col2:
                st.metric("Avg Sources", f"{eval_results.get('avg_sources_count', 0):.1f}")
                st.metric("Avg Coverage", f"{eval_results.get('avg_coverage_score', 0):.1%}")
                
            # Show sub-question coverage if available
            if "avg_sub_question_coverage" in eval_results:
                st.metric("Sub-Q Coverage", f"{eval_results.get('avg_sub_question_coverage', 0):.1%}")
                
        elif "results" in eval_results and eval_results["results"]:
            # Multi-result format - show recent results
            recent_results = eval_results["results"][-3:]  # Last 3 results
            
            st.write("**Recent Performance:**")
            for i, result in enumerate(recent_results, 1):
                if result.get("success"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(f"Run {i} Duration", f"{result.get('duration_s', 0):.1f}s")
                    with col2:
                        st.metric(f"Run {i} Sources", result.get('sources_count', 0))
                    with col3:
                        st.metric(f"Run {i} Coverage", f"{result.get('coverage_score', 0):.1%}")
        else:
            st.info("📊 Run evaluation to see benchmark data")
            
    except Exception as e:
        st.error(f"Could not load benchmark data: {e}")
        st.info("💡 Try running: `uv run python eval/harness.py --quick`")


def _render_status_panel():
    """Render research status panel with Stage 1.5 real-time progress."""
    if st.session_state.research_running:
        st.info("🔄 Research Active")
        
        # Stage 1.5: Real-time progress tracking
        if st.session_state.research_state:
            state = st.session_state.research_state
            
            # Progress bar
            progress_percent = state.get('progress_percent', 0.0)
            st.progress(progress_percent)
            
            # Status and ETA
            status = state.get('status', 'unknown').title()
            st.write(f"**Status:** {status}")
            
            # Calculate and show ETA
            start_time = st.session_state.research_start_time
            if start_time and progress_percent > 0:
                eta_seconds = estimate_eta(progress_percent, start_time)
                if eta_seconds:
                    eta_formatted = format_eta(eta_seconds)
                    st.write(f"**ETA:** {eta_formatted}")
                    
            # Show current progress percentage
            st.write(f"**Progress:** {int(progress_percent * 100)}%")
            
            # Show partial failures if any
            partial_failures = state.get('partial_failures', [])
            if partial_failures:
                st.warning(f"⚠️ {len(partial_failures)} non-fatal issues occurred")
                with st.expander("View Issues"):
                    for failure in partial_failures:
                        st.write(f"• **{failure.get('source', 'Unknown')}**: {failure.get('error', 'Unknown error')}")
        else:
            # Fallback indeterminate progress
            st.progress(0.5)
        
    elif st.session_state.research_results:
        results = st.session_state.research_results
        
        if results["success"]:
            st.success("✅ Research Complete")
            
            # Show key metrics
            metrics = results.get("metrics", {})
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Duration", f"{metrics.get('duration_s', 0):.1f}s")
                st.metric("Sources", metrics.get('sources_count', 0))
            
            with col2:
                st.metric("Claims", len(results.get("state", {}).get("claims", [])))
                st.metric("Word Count", results.get("report", {}).get("word_count", 0))
        else:
            st.error("❌ Research Failed")
            st.error(results.get("error", "Unknown error"))
    else:
        st.info("⏳ Ready for Research")


def _run_research(topic: str, constraints: Constraints, selected_model: str):
    """Execute research pipeline asynchronously with Stage 1.5 progress tracking."""
    st.session_state.research_running = True
    st.session_state.research_logs = []
    st.session_state.research_start_time = time.time()  # Stage 1.5: Track start time
    
    # Set the selected model in config for this session
    Config.SELECTED_MODEL = selected_model
    
    # Create progress indicators
    progress_container = st.container()
    
    with progress_container:
        st.info("🚀 Starting research pipeline...")
        # Stage 1.5: Enhanced progress tracking
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        eta_text = st.empty()
    
    try:
        # Stage 1.5: Run research with progress monitoring
        class ProgressCallback:
            def __init__(self, progress_bar, status_text, eta_text):
                self.last_update = time.time()
                self.progress_bar = progress_bar
                self.status_text = status_text
                self.eta_text = eta_text
                
            def update_progress(self, state):
                # Throttle updates to avoid too many reruns
                now = time.time()
                if now - self.last_update > 0.5:  # Update every 0.5 seconds max
                    st.session_state.research_state = state
                    
                    # Update UI elements directly
                    progress_percent = state.get('progress_percent', 0.0)
                    status = state.get('status', 'unknown').title()
                    
                    self.progress_bar.progress(progress_percent)
                    self.status_text.write(f"**Status:** {status}")
                    
                    # Calculate and show ETA
                    start_time = st.session_state.research_start_time
                    if start_time and progress_percent > 0:
                        eta_seconds = estimate_eta(progress_percent, start_time)
                        if eta_seconds:
                            eta_formatted = format_eta(eta_seconds)
                            self.eta_text.write(f"**ETA:** {eta_formatted}")
                    
                    self.last_update = now
        
        callback = ProgressCallback(progress_bar, status_text, eta_text)
        
        # Run research pipeline with progress monitoring
        results = asyncio.run(_run_research_with_monitoring(
            topic, constraints, selected_model, callback
        ))
        
        # Store results
        st.session_state.research_results = results
        st.session_state.research_running = False
        st.session_state.research_state = None  # Clear progress state
        
        # Clear progress indicators
        progress_bar.progress(1.0)
        status_text.success("✅ Research completed!")
        
        # Force rerun to update UI
        st.rerun()
        
    except Exception as e:
        st.session_state.research_running = False
        st.session_state.research_state = None
        st.session_state.research_results = {
            "success": False,
            "error": str(e),
            "state": None,
            "report": None
        }
        
        # Show error
        progress_container.error(f"❌ Research failed: {str(e)}")
        
        logger.error(f"Research failed in UI: {e}")


async def _run_research_with_monitoring(topic: str, constraints: Constraints, selected_model: str, callback):
    """Run research pipeline with progress monitoring."""
    # Now the orchestrator supports callbacks!
    return await run_research_pipeline(
        topic=topic,
        constraints=constraints,
        selected_model=selected_model,
        progress_callback=callback.update_progress
    )


def _render_results_section():
    """Render research results section."""
    results = st.session_state.research_results
    
    if not results or not results["success"]:
        return
    
    st.header("📋 Research Report")
    
    report = results.get("report")
    if not report:
        st.warning("No report generated")
        return
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Report", "📊 Metrics", "🔗 Sources", "💾 Export"])
    
    with tab1:
        # Main report content
        st.markdown(report["report_md"])
    
    with tab2:
        # Research metrics
        _render_metrics_tab(results)
    
    with tab3:
        # Sources and citations
        _render_sources_tab(results)
    
    with tab4:
        # Export options
        _render_export_tab(results)


def _render_metrics_tab(results: Dict[str, Any]):
    """Render metrics tab."""
    st.subheader("📊 Research Metrics")
    
    state = results.get("state", {})
    metrics = results.get("metrics", {})
    report = results.get("report", {})
    
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Duration", f"{metrics.get('duration_s', 0):.1f}s")
    with col2:
        st.metric("Sources Found", metrics.get('sources_count', 0))
    with col3:
        st.metric("Claims Extracted", len(state.get('claims', [])))
    with col4:
        st.metric("Word Count", report.get('word_count', 0))
    
    # Pipeline breakdown
    st.subheader("🔄 Pipeline Breakdown")
    
    pipeline_data = {
        "Search Queries": len(state.get('queries', [])),
        "Search Results": len(state.get('search_results', [])),
        "Documents Processed": len(state.get('documents', [])),
        "Content Chunks": len(state.get('chunks', [])),
        "Claims Verified": len(state.get('claims', [])),
        "Citations Created": len(state.get('citations', []))
    }
    
    for label, value in pipeline_data.items():
        st.metric(label, value)
    
    # Claims breakdown by type
    claims = state.get('claims', [])
    if claims:
        st.subheader("📝 Claims Analysis")
        
        claim_types = {}
        confidence_scores = []
        
        for claim in claims:
            claim_type = claim.get('type', 'unknown')
            claim_types[claim_type] = claim_types.get(claim_type, 0) + 1
            confidence_scores.append(claim.get('confidence', 0))
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Claims by Type:**")
            for claim_type, count in claim_types.items():
                st.write(f"- {claim_type.title()}: {count}")
        
        with col2:
            if confidence_scores:
                avg_confidence = sum(confidence_scores) / len(confidence_scores)
                st.metric("Average Confidence", f"{avg_confidence:.2f}")


def _render_sources_tab(results: Dict[str, Any]):
    """Render sources and citations tab."""
    st.subheader("🔗 Sources & Citations")
    
    report = results.get("report", {})
    state = results.get("state", {})
    
    # References from report
    references = report.get("references", [])
    if references:
        st.write("**References:**")
        for ref in references:
            st.write(f"{ref['number']}. [{ref.get('title', 'Link')}]({ref['url']})")
    
    # Document sources
    documents = state.get('documents', [])
    if documents:
        st.subheader("📄 Source Documents")
        
        for i, doc in enumerate(documents, 1):
            with st.expander(f"Source {i}: {doc.get('title', 'Untitled')}"):
                st.write(f"**URL:** {doc['url']}")
                st.write(f"**Content Type:** {doc.get('content_type', 'Unknown')}")
                
                source_meta = doc.get('source_meta', {})
                if source_meta:
                    st.write(f"**Domain:** {source_meta.get('domain', 'Unknown')}")
                    st.write(f"**Content Length:** {source_meta.get('content_length', 0)} chars")
                
                # Show snippet
                text = doc.get('text', '')
                if text:
                    snippet = text[:500] + "..." if len(text) > 500 else text
                    st.text_area("Content Preview", snippet, height=100, disabled=True, key=f"content_preview_{i}")


def _render_export_tab(results: Dict[str, Any]):
    """Render export options tab."""
    st.subheader("💾 Export Options")
    
    report = results.get("report", {})
    if not report:
        st.warning("No report to export")
        return
    
    # Markdown export
    st.write("**Markdown Report:**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Download markdown
        report_md = report.get("report_md", "")
        if report_md:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"nova_brief_report_{timestamp}.md"
            
            st.download_button(
                label="📄 Download Markdown",
                data=report_md,
                file_name=filename,
                mime="text/markdown"
            )
    
    with col2:
        # Download JSON
        report_json = json.dumps(report, indent=2, default=str)
        filename_json = f"nova_brief_data_{timestamp}.json"
        
        st.download_button(
            label="📊 Download JSON",
            data=report_json,
            file_name=filename_json,
            mime="application/json"
        )
    
    # Preview section
    st.write("**Preview:**")
    with st.expander("Markdown Preview", expanded=False):
        st.code(report.get("report_md", ""), language="markdown")


def _render_logs_section():
    """Render research logs section."""
    logs = st.session_state.research_logs
    
    if not logs:
        st.info("No logs available")
        return
    
    # Display logs in reverse chronological order
    for log_entry in reversed(logs):
        timestamp = log_entry.get('timestamp', '')
        level = log_entry.get('level', 'INFO')
        message = log_entry.get('message', '')
        
        # Style based on log level
        if level == 'ERROR':
            st.error(f"[{timestamp}] {message}")
        elif level == 'WARNING':
            st.warning(f"[{timestamp}] {message}")
        else:
            st.info(f"[{timestamp}] {message}")


if __name__ == "__main__":
    main()