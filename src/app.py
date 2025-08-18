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
    
    # Clean header without duplication
    pass  # Header is now handled in state-aware rendering
    
    # Check environment setup
    if not _check_environment():
        st.error("⚠️ Environment not properly configured. Please set required API keys.")
        st.stop()
    
    # Sidebar for configuration
    with st.sidebar:
        st.markdown("### ⚙️ Setup")
        
        # Model selection
        selected_model = _render_hierarchical_model_selection()
        
        # Research constraints
        constraints = _render_progressive_constraints_form()
        
        # API Configuration status
        _render_compact_api_status(selected_model)
        
        # Minimal about section
        st.markdown("---")
        st.caption("**Nova Brief** generates research reports with verified citations from multiple sources.")
    
    # State-aware main panel layout
    _render_state_aware_main_panel(constraints, selected_model)
    
    # Results section
    if st.session_state.research_results:
        _render_results_section()


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


def _render_hierarchical_model_selection() -> str:
    """Render two-tier hierarchical model selection: Provider → Model."""
    st.subheader("🤖 Model Selection")
    
    # Get available models and organize by provider
    available_models_dict = Config.get_available_models_dict()
    current_selection = Config.SELECTED_MODEL
    
    # Organize by provider for hierarchical selection
    provider_groups = {
        "openrouter": {
            "display": "🔗 OpenRouter",
            "models": {},
            "description": "Multiple models via OpenRouter aggregation"
        },
        "openai": {
            "display": "🤖 OpenAI Direct",
            "models": {},
            "description": "Direct OpenAI API access"
        },
        "anthropic": {
            "display": "🧠 Anthropic Direct",
            "models": {},
            "description": "Direct Anthropic API access"
        },
        "google": {
            "display": "🔍 Google Direct",
            "models": {},
            "description": "Direct Google AI API access"
        }
    }
    
    # Populate models by provider
    for model_key, model_config in available_models_dict.items():
        provider = model_config.provider
        if provider in provider_groups:
            # Create display name for model
            base_model_key = None
            for base_key, variants in Config.BASE_MODELS.items():
                if model_key in Config.get_models_by_base_model(base_key):
                    base_model_key = base_key
                    break
            
            if base_model_key:
                base_config = Config.BASE_MODELS[base_model_key]
                display_name = base_config['name']
                
                # Add inference method indicator
                if model_config.provider_params:
                    if "cerebras" in str(model_config.provider_params):
                        display_name += " 🧠 (Cerebras)"
                    else:
                        display_name += f" ({model_config.provider_params})"
                elif provider == "openrouter":
                    display_name += " (Default)"
                
                provider_groups[provider]["models"][model_key] = display_name
    
    # Get current provider and model
    current_provider = "openrouter"  # default
    current_model = current_selection
    
    if current_selection in available_models_dict:
        current_provider = available_models_dict[current_selection].provider
    
    # Initialize session state for hierarchical selection
    if 'selected_provider' not in st.session_state:
        st.session_state.selected_provider = current_provider
    if 'selected_model_key' not in st.session_state:
        st.session_state.selected_model_key = current_model
    
    # Provider selection
    provider_options = list(provider_groups.keys())
    provider_displays = [provider_groups[p]["display"] for p in provider_options]
    
    try:
        provider_index = provider_options.index(st.session_state.selected_provider)
    except ValueError:
        provider_index = 0
        st.session_state.selected_provider = provider_options[0]
    
    selected_provider = st.selectbox(
        "Choose Provider:",
        options=provider_options,
        index=provider_index,
        format_func=lambda x: provider_groups[x]["display"],
        help=provider_groups[st.session_state.selected_provider]["description"],
        key="provider_selectbox"
    )
    
    # Update provider in session state
    if selected_provider != st.session_state.selected_provider:
        st.session_state.selected_provider = selected_provider
        # Reset model selection when provider changes
        available_models = list(provider_groups[selected_provider]["models"].keys())
        if available_models:
            st.session_state.selected_model_key = available_models[0]
        st.rerun()
    
    # Model selection for chosen provider
    available_models = provider_groups[selected_provider]["models"]
    
    if not available_models:
        st.warning(f"No models available for {provider_groups[selected_provider]['display']}")
        return current_selection
    
    model_keys = list(available_models.keys())
    model_displays = list(available_models.values())
    
    # Find current model index
    try:
        model_index = model_keys.index(st.session_state.selected_model_key)
    except ValueError:
        model_index = 0
        st.session_state.selected_model_key = model_keys[0]
    
    selected_model_key = st.selectbox(
        "Choose Model:",
        options=model_keys,
        index=model_index,
        format_func=lambda x: available_models[x],
        help="Select specific model configuration and inference method",
        key="model_selectbox"
    )
    
    # Update model in session state
    if selected_model_key != st.session_state.selected_model_key:
        st.session_state.selected_model_key = selected_model_key
        st.rerun()
    
    # Show selection details
    if selected_model_key in available_models_dict:
        model_config = available_models_dict[selected_model_key]
        
        # API key status indicator
        api_key = os.getenv(model_config.api_key_env)
        if api_key:
            st.success(f"✅ {model_config.api_key_env} configured")
        else:
            st.error(f"❌ {model_config.api_key_env} required")
        
        # Model details in compact format
        with st.expander("📋 Model Details", expanded=False):
            st.write(f"**Model ID:** `{model_config.model_id}`")
            st.write(f"**Provider:** {model_config.provider.title()}")
            if model_config.provider_params:
                st.write(f"**Parameters:** {model_config.provider_params}")
            if model_config.base_url:
                st.write(f"**Endpoint:** {model_config.base_url}")
    
    return selected_model_key


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


def _render_progressive_constraints_form() -> Constraints:
    """Render research constraints with progressive disclosure."""
    st.subheader("🎛️ Research Settings")
    
    # Load defaults
    defaults = create_default_constraints()
    
    # Primary control - always visible
    max_rounds = st.slider(
        "Max Research Rounds",
        min_value=1,
        max_value=5,
        value=defaults["max_rounds"],
        help="Number of iterative research rounds to perform"
    )
    
    # Advanced settings in expandable section
    with st.expander("⚙️ Advanced Settings", expanded=False):
        st.write("**Performance & Quality Controls**")
        
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
            "Timeout (seconds)",
            min_value=5,
            max_value=30,
            value=int(defaults["fetch_timeout_s"]),
            help="Page fetch timeout"
        )
        
        st.write("**Domain Filters**")
        
        include_domains_text = st.text_area(
            "Focus Domains (one per line)",
            placeholder="edu\ngov\norg",
            height=60,
            help="Prioritize these domains"
        )
        
        exclude_domains_text = st.text_area(
            "Exclude Domains (one per line)",
            placeholder="reddit.com\nforum.example.com",
            height=60,
            help="Skip these domains"
        )
    
    # Parse domain filters (default to empty if not in expander)
    include_domains = []
    exclude_domains = []
    if include_domains_text:
        include_domains = [d.strip() for d in include_domains_text.split('\n') if d.strip()]
    if exclude_domains_text:
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


def _render_compact_api_status(selected_model: str):
    """Render compact API status with expandable details."""
    st.subheader("🔑 API Status")
    
    available_models = Config.get_available_models_dict()
    model_config = available_models.get(selected_model)
    
    if not model_config:
        st.error("❌ Invalid model configuration")
        return
    
    # Compact status line
    api_key = os.getenv(model_config.api_key_env)
    
    if api_key:
        st.success("✅ Ready")
    else:
        st.error("❌ Configure API Key")
        st.warning(f"Missing: {model_config.api_key_env}")
    
    # Expandable details
    with st.expander("View Details", expanded=not api_key):
        if api_key:
            # Show partial key for verification
            masked_key = f"{api_key[:8]}...{api_key[-4:]}"
            st.success(f"✅ {model_config.api_key_env}")
            st.code(masked_key)
        else:
            st.error(f"❌ {model_config.api_key_env} Missing")
            
            # Show setup instructions based on provider
            if model_config.provider == "google":
                st.info("💡 [Get Google AI API key](https://aistudio.google.com/app/apikey)")
            elif model_config.provider == "anthropic":
                st.info("💡 [Get Anthropic API key](https://console.anthropic.com/)")
            elif model_config.provider == "openai":
                st.info("💡 [Get OpenAI API key](https://platform.openai.com/api-keys)")
            elif model_config.provider == "openrouter":
                st.info("💡 [Get OpenRouter API key](https://openrouter.ai/keys)")
            
            st.code(f"# Add to .env file:\n{model_config.api_key_env}=your_key_here")
        
        # Technical details
        st.write("**Configuration Details:**")
        st.write(f"• **Model:** `{model_config.model_id}`")
        st.write(f"• **Provider:** {model_config.provider.title()}")
        
        if model_config.provider_params:
            st.write(f"• **Parameters:** {model_config.provider_params}")
        
        if model_config.base_url:
            st.write(f"• **Endpoint:** `{model_config.base_url}`")


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


def _render_state_aware_main_panel(constraints, selected_model):
    """Render main panel that adapts to current UI state."""
    
    # Determine current UI state
    ui_state = _get_ui_state()
    
    if ui_state == "ready":
        _render_ready_state(constraints, selected_model)
    elif ui_state == "running":
        _render_running_state()
    elif ui_state == "results":
        _render_results_state()


def _get_ui_state() -> str:
    """Determine current UI state based on session state."""
    if st.session_state.research_running:
        return "running"
    elif st.session_state.research_results:
        return "results"
    else:
        return "ready"


def _render_ready_state(constraints, selected_model):
    """Render the ready state with clean input interface."""
    
    # Professional tagline with better description
    st.markdown("### 🔍 Nova Brief")
    st.markdown("**Transform any topic into a comprehensive research report with verified sources and citations**")
    st.markdown("---")
    
    # Main content area with better layout
    st.markdown("")  # Add spacing
    
    # Topic input section
    st.markdown("#### What would you like to research?")
    
    # Initialize session state for topic if not exists
    if 'research_topic' not in st.session_state:
        st.session_state.research_topic = ""
    
    # Topic input without placeholder text
    topic = st.text_area(
        label="Research Topic",
        value=st.session_state.research_topic,
        height=80,
        help="Enter a specific research question or topic. Include timeframes, locations, or specific aspects for best results.",
        label_visibility="collapsed"
    )
    
    # Update session state
    if topic != st.session_state.research_topic:
        st.session_state.research_topic = topic
    
    # Example queries section with clickable buttons
    st.markdown("##### Quick Start Examples:")
    
    # Create columns for example buttons
    example_cols = st.columns(3)
    
    example_queries = [
        ("🏥 Healthcare AI", "Impact of artificial intelligence on diagnostic accuracy in healthcare 2023-2024"),
        ("🚗 EV Adoption", "Electric vehicle adoption trends and infrastructure challenges in Europe 2024"),
        ("🏢 Remote Work", "Long-term effects of remote work on commercial real estate values post-pandemic"),
        ("🌱 Climate Tech", "Breakthrough carbon capture technologies and their commercial viability in 2024"),
        ("💻 Quantum Computing", "Recent advances in quantum computing error correction methods"),
        ("🧬 Gene Therapy", "CRISPR gene therapy clinical trials and FDA approvals in 2024")
    ]
    
    # Display example buttons in grid
    for idx, (label, query) in enumerate(example_queries):
        col_idx = idx % 3
        with example_cols[col_idx]:
            if st.button(label, key=f"example_{idx}", use_container_width=True):
                st.session_state.research_topic = query
                st.rerun()
    
    st.markdown("")  # Add spacing
    
    # Validation and action buttons row
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        # Validation messages
        if topic:
            validation = validate_pipeline_inputs(topic, constraints)
            if not validation["valid"]:
                for issue in validation["issues"]:
                    st.error(f"❌ {issue}")
            else:
                st.success("✅ Topic is valid and ready for research")
    
    with col2:
        # Research button
        if st.button(
            "🚀 Start Research",
            disabled=not topic or st.session_state.research_running,
            type="primary",
            use_container_width=True
        ):
            if topic and not st.session_state.research_running:
                # Store topic and constraints for display during research
                st.session_state.current_topic = topic
                st.session_state.last_constraints = constraints
                _run_research(topic, constraints, selected_model)
    
    with col3:
        # Status and timing info
        if topic and not st.session_state.research_running:
            st.info(f"⏱️ Estimated time: {constraints['max_rounds'] * 60}-{constraints['max_rounds'] * 90} seconds")


def _render_running_state():
    """Render the running state with progress dashboard."""
    
    # Clean progress header
    topic = getattr(st.session_state, 'current_topic', 'Research')
    st.markdown("### 🔄 Research in Progress")
    st.markdown(f"**Topic:** {topic}")
    st.markdown("---")
    
    # Progress tracking
    if st.session_state.research_state:
        state = st.session_state.research_state
        
        # Main progress bar
        progress_percent = state.get('progress_percent', 0.0)
        st.progress(progress_percent)
        
        # Status and metrics row
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status = state.get('status', 'unknown').title()
            st.metric("Current Step", status)
        
        with col2:
            st.metric("Progress", f"{int(progress_percent * 100)}%")
        
        with col3:
            # Calculate and show ETA
            start_time = st.session_state.research_start_time
            if start_time and progress_percent > 0:
                eta_seconds = estimate_eta(progress_percent, start_time)
                if eta_seconds:
                    eta_formatted = format_eta(eta_seconds)
                    st.metric("ETA", eta_formatted)
        
        # Show step indicator
        step_names = ["Planning", "Searching", "Reading", "Analyzing", "Verifying", "Writing"]
        current_step = min(int(progress_percent * 6), 5)
        
        step_indicators = []
        for i, step in enumerate(step_names):
            if i < current_step:
                step_indicators.append(f"✅ {step}")
            elif i == current_step:
                step_indicators.append(f"🔄 {step}")
            else:
                step_indicators.append(f"⏳ {step}")
        
        st.write("**Pipeline Progress:**")
        st.write(" → ".join(step_indicators))
        
        # Show partial failures if any
        partial_failures = state.get('partial_failures', [])
        if partial_failures:
            st.warning(f"⚠️ {len(partial_failures)} non-fatal issues occurred")
            with st.expander("View Issues"):
                for failure in partial_failures[:5]:  # Show max 5
                    st.write(f"• **{failure.get('source', 'Unknown')}**: {failure.get('error', 'Unknown error')}")
                if len(partial_failures) > 5:
                    st.write(f"... and {len(partial_failures) - 5} more")
    
    # Live logs section with cleaner header
    st.markdown("")  # Add spacing
    st.markdown("#### 📝 Live Activity")
    _render_live_logs()


def _render_results_state():
    """Render the results state with enhanced tabs."""
    results = st.session_state.research_results
    
    if not results or not results["success"]:
        st.markdown("### ❌ Research Failed")
        if results and results.get("error"):
            st.error(f"Error: {results['error']}")
        
        # Add button to return to ready state
        if st.button("🔄 Start New Research", type="primary"):
            st.session_state.research_results = None
            st.session_state.research_topic = ""
            st.rerun()
        return
    
    # Clean results header
    st.markdown("### ✅ Research Complete")
    topic = getattr(st.session_state, 'current_topic', results.get("topic", "Research"))
    st.markdown(f"**Topic:** {topic}")
    st.markdown("---")
    
    # Summary metrics
    metrics = results.get("metrics", {})
    state = results.get("state", {})
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Duration", f"{metrics.get('duration_s', 0):.1f}s")
    with col2:
        st.metric("Sources", metrics.get('sources_count', 0))
    with col3:
        st.metric("Claims", len(state.get('claims', [])))
    with col4:
        st.metric("Word Count", results.get("report", {}).get("word_count", 0))
    
    # Enhanced results tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Brief", "🗺️ Evidence Map", "🔗 Sources", "📊 Details"])
    
    with tab1:
        _render_brief_tab(results)
    
    with tab2:
        _render_evidence_map_tab(results)
    
    with tab3:
        _render_enhanced_sources_tab(results)
    
    with tab4:
        _render_details_tab(results)
    
    # Action buttons row
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🔄 New Research", type="primary", use_container_width=True):
            st.session_state.research_results = None
            st.session_state.research_topic = ""
            st.rerun()
    with col2:
        if st.button("📤 Share", use_container_width=True):
            st.info("Sharing functionality coming soon!")
    with col3:
        # Empty column for spacing
        pass


def _render_live_logs():
    """Render live streaming logs during research execution."""
    logs = getattr(st.session_state, 'live_logs', [])
    
    if not logs:
        st.info("Waiting for research to begin...")
        return
    
    # Create a container for logs that updates
    log_container = st.container()
    
    with log_container:
        # Show recent logs (last 20 entries)
        recent_logs = logs[-20:] if len(logs) > 20 else logs
        
        for log_entry in reversed(recent_logs):  # Most recent first
            timestamp = log_entry.get('timestamp', '')
            if isinstance(timestamp, float):
                timestamp = datetime.fromtimestamp(timestamp).strftime("%H:%M:%S")
            
            level = log_entry.get('level', 'INFO')
            message = log_entry.get('message', '')
            
            # Style based on log level
            if level == 'ERROR':
                st.error(f"[{timestamp}] {message}")
            elif level == 'WARNING':
                st.warning(f"[{timestamp}] {message}")
            else:
                st.info(f"[{timestamp}] {message}")


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


def _render_brief_tab(results):
    """Render the main brief/report tab."""
    report = results.get("report")
    if not report:
        st.warning("No report generated")
        return
    
    # Extract markdown content, handling both parsed and raw JSON cases
    markdown_content = ""
    
    # First try to get parsed markdown
    if isinstance(report, dict) and "report_md" in report:
        markdown_content = report.get("report_md", "")
    elif isinstance(report, str):
        # Handle case where report is raw JSON string
        try:
            import json
            parsed_report = json.loads(report)
            markdown_content = parsed_report.get("report_markdown", "")
        except (json.JSONDecodeError, KeyError):
            # If JSON parsing fails, treat as plain text
            markdown_content = report
    else:
        # Fallback for other cases
        markdown_content = str(report)
    
    # Display the markdown content
    if markdown_content:
        st.markdown(markdown_content)
    else:
        st.warning("No report content available")
    
    # Download button
    if markdown_content:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nova_brief_report_{timestamp}.md"
        
        st.download_button(
            label="📄 Download Report",
            data=markdown_content,
            file_name=filename,
            mime="text/markdown",
            type="primary"
        )


def _render_evidence_map_tab(results):
    """Render the Evidence Map tab with improved layout and pagination."""
    st.markdown("### 🗺️ Evidence Map")
    st.caption("Interactive mapping between claims and supporting sources")
    
    state = results.get("state", {})
    claims = state.get("claims", [])
    citations = state.get("citations", [])
    documents = state.get("documents", [])
    
    if not claims:
        st.info("No claims extracted during research")
        return
    
    # Create claims-to-sources mapping
    claim_source_map = {}
    for citation in citations:
        claim_id = citation.get("claim_id")
        urls = citation.get("urls", [])
        if claim_id:
            claim_source_map[claim_id] = urls
    
    # Initialize session state for selected claim and pagination
    if 'selected_claim' not in st.session_state:
        st.session_state.selected_claim = None
    if 'selected_claim_index' not in st.session_state:
        st.session_state.selected_claim_index = 0
    if 'claims_page' not in st.session_state:
        st.session_state.claims_page = 0
    
    # Pagination settings
    claims_per_page = 7
    total_pages = (len(claims) - 1) // claims_per_page + 1
    
    # Better layout with 40-60 split
    col1, col2 = st.columns([4, 6])
    
    with col1:
        st.markdown("#### 📝 Claims List")
        st.markdown(f"*{len(claims)} claims extracted*")
        
        # Pagination controls
        if total_pages > 1:
            pagination_col1, pagination_col2, pagination_col3 = st.columns([1, 2, 1])
            
            with pagination_col1:
                if st.button("◀️ Prev", disabled=st.session_state.claims_page == 0, key="prev_claims"):
                    st.session_state.claims_page = max(0, st.session_state.claims_page - 1)
                    st.rerun()
            
            with pagination_col2:
                st.markdown(f"<div style='text-align: center; padding: 5px;'>Page {st.session_state.claims_page + 1} of {total_pages}</div>", unsafe_allow_html=True)
            
            with pagination_col3:
                if st.button("Next ▶️", disabled=st.session_state.claims_page == total_pages - 1, key="next_claims"):
                    st.session_state.claims_page = min(total_pages - 1, st.session_state.claims_page + 1)
                    st.rerun()
        
        # Calculate current page claims
        start_idx = st.session_state.claims_page * claims_per_page
        end_idx = min(start_idx + claims_per_page, len(claims))
        current_page_claims = claims[start_idx:end_idx]
        
        # Create a scrollable container for claims
        claims_container = st.container()
        with claims_container:
            # Add custom CSS for better scrolling
            st.markdown("""
            <style>
            .claim-item {
                padding: 10px;
                margin: 5px 0;
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.2s;
            }
            .claim-item:hover {
                background-color: #f0f2f6;
            }
            .claim-selected {
                background-color: #e3f2fd;
                border-left: 3px solid #1976d2;
            }
            .claim-confidence {
                display: inline-block;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 0.8em;
                margin-left: 5px;
            }
            .confidence-high { background-color: #c8e6c9; color: #2e7d32; }
            .confidence-medium { background-color: #fff3e0; color: #f57c00; }
            .confidence-low { background-color: #ffebee; color: #c62828; }
            </style>
            """, unsafe_allow_html=True)
            
            # Display claims for current page
            for page_idx, claim in enumerate(current_page_claims):
                actual_idx = start_idx + page_idx
                claim_id = claim.get("id", f"claim_{actual_idx}")
                claim_text = claim.get("text", "Unknown claim")
                confidence = claim.get("confidence", 0)
                claim_type = claim.get("type", "unknown")
                
                # Determine confidence level for styling
                if confidence > 0.7:
                    conf_class = "confidence-high"
                    conf_icon = "✅"
                elif confidence > 0.4:
                    conf_class = "confidence-medium"
                    conf_icon = "⚠️"
                else:
                    conf_class = "confidence-low"
                    conf_icon = "❌"
                
                # Create a more compact claim display
                is_selected = st.session_state.selected_claim == claim_id
                
                # Use columns for better layout
                claim_col1, claim_col2 = st.columns([10, 1])
                
                with claim_col1:
                    if st.button(
                        f"{actual_idx+1}. {claim_text[:80]}{'...' if len(claim_text) > 80 else ''}",
                        key=f"claim_btn_{actual_idx}",
                        use_container_width=True,
                        type="primary" if is_selected else "secondary"
                    ):
                        st.session_state.selected_claim = claim_id
                        st.session_state.selected_claim_index = actual_idx
                        st.rerun()
                
                with claim_col2:
                    st.markdown(f"<span class='claim-confidence {conf_class}'>{conf_icon}</span>",
                              unsafe_allow_html=True)
                
                # Show metadata below the button
                if is_selected:
                    st.caption(f"Type: {claim_type.title()} | Confidence: {confidence:.2f}")
                    sources_count = len(claim_source_map.get(claim_id, []))
                    st.caption(f"📚 {sources_count} source(s)")
    
    with col2:
        st.markdown("#### 📚 Supporting Evidence")
        
        if st.session_state.selected_claim:
            # Show selected claim details
            selected_index = st.session_state.selected_claim_index
            selected_claim = claims[selected_index]
            
            # Claim details card
            st.markdown(f"""
            <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                <strong>Claim #{selected_index + 1}</strong><br>
                <span style="color: #495057; font-size: 0.95em;">{selected_claim.get('text', '')}</span><br>
                <small style="color: #6c757d;">
                    Type: {selected_claim.get('type', 'unknown').title()} |
                    Confidence: {selected_claim.get('confidence', 0):.2f}
                </small>
            </div>
            """, unsafe_allow_html=True)
            
            # Show sources for selected claim
            supporting_urls = claim_source_map.get(st.session_state.selected_claim, [])
            
            if supporting_urls:
                st.success(f"📖 {len(supporting_urls)} supporting source(s) found")
                
                # Create tabs for sources if multiple
                if len(supporting_urls) > 1:
                    source_tabs = st.tabs([f"Source {j+1}" for j in range(len(supporting_urls))])
                    
                    for j, (url, tab) in enumerate(zip(supporting_urls, source_tabs)):
                        with tab:
                            _render_source_content(url, documents, j)
                else:
                    # Single source, no tabs needed
                    _render_source_content(supporting_urls[0], documents, 0)
            else:
                st.warning("⚠️ No supporting sources found for this claim")
                st.info("This claim may need additional verification or may be based on inference from the available data.")
        else:
            # Empty state with better guidance
            st.markdown("""
            <div style="text-align: center; padding: 40px; background-color: #f8f9fa; border-radius: 8px;">
                <h4 style="color: #6c757d;">👈 Select a claim to view evidence</h4>
                <p style="color: #868e96;">Click on any claim from the list to see its supporting sources and evidence.</p>
            </div>
            """, unsafe_allow_html=True)


def _render_source_content(url: str, documents: list, index: int):
    """Helper function to render source content consistently."""
    # Find corresponding document
    supporting_doc = None
    for doc in documents:
        if doc.get("url") == url:
            supporting_doc = doc
            break
    
    if supporting_doc:
        title = supporting_doc.get("title", "Untitled")
        domain = supporting_doc.get("source_meta", {}).get("domain", "Unknown")
        
        # Source header
        st.markdown(f"""
        <div style="background-color: #e7f3ff; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
            <strong>🔗 {title}</strong><br>
            <small style="color: #6c757d;">{domain} | <a href="{url}" target="_blank">Open Source</a></small>
        </div>
        """, unsafe_allow_html=True)
        
        # Content preview with better formatting
        text = supporting_doc.get("text", "")
        if text:
            # Show more content but in a scrollable area
            st.markdown("**📄 Content Preview:**")
            snippet = text[:1500] + "..." if len(text) > 1500 else text
            
            # Use a styled text area for better readability
            st.markdown(f"""
            <div style="background-color: white; padding: 15px; border: 1px solid #dee2e6;
                        border-radius: 5px; max-height: 400px; overflow-y: auto;
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;">
                {snippet}
            </div>
            """, unsafe_allow_html=True)
            
            # Metadata
            st.caption(f"Content length: {len(text):,} characters")
    else:
        # Fallback for URL without document
        st.markdown(f"""
        <div style="background-color: #fff3cd; padding: 10px; border-radius: 5px;">
            <strong>🔗 Source URL</strong><br>
            <a href="{url}" target="_blank">{url}</a><br>
            <small style="color: #856404;">Document content not available</small>
        </div>
        """, unsafe_allow_html=True)


def _render_enhanced_sources_tab(results):
    """Render unified sources tab without redundancy."""
    st.subheader("🔗 Sources & References")
    
    report = results.get("report", {})
    state = results.get("state", {})
    
    # Get references and documents
    references = report.get("references", [])
    documents = state.get("documents", [])
    
    if not documents and not references:
        st.info("No sources were processed during this research.")
        return
    
    # Create a unified view by mapping citations to documents
    cited_urls = {ref.get("url") for ref in references if ref.get("url")}
    
    # Group documents by citation status and domain
    cited_docs = []
    uncited_docs = []
    
    for doc in documents:
        if doc.get("url") in cited_urls:
            cited_docs.append(doc)
        else:
            uncited_docs.append(doc)
    
    # Show summary stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📚 Total Sources", len(documents))
    with col2:
        st.metric("📝 Cited Sources", len(cited_docs))
    with col3:
        st.metric("📄 Referenced in Report", len(references))
    
    st.markdown("---")
    
    # Cited sources section
    if cited_docs:
        st.markdown("### 📝 Cited Sources")
        st.caption("Sources that were referenced in the final report")
        
        # Group cited sources by domain
        domain_groups = {}
        for doc in cited_docs:
            url = doc.get("url", "")
            domain = url.split("//")[-1].split("/")[0] if "//" in url else "unknown"
            if domain not in domain_groups:
                domain_groups[domain] = []
            domain_groups[domain].append(doc)
        
        for domain, docs in domain_groups.items():
            with st.expander(f"🌐 {domain} ({len(docs)} sources)", expanded=len(domain_groups) <= 2):
                for doc in docs:
                    # Find corresponding reference number
                    ref_number = "?"
                    doc_url = doc.get("url")
                    for ref in references:
                        if ref.get("url") == doc_url:
                            ref_number = ref.get("number", "?")
                            break
                    
                    title = doc.get("title", "Untitled")
                    content_length = len(doc.get("text", ""))
                    
                    st.markdown(f"**[{ref_number}] {title}**")
                    st.markdown(f"🔗 [Open Source]({doc_url})")
                    st.caption(f"Content: {content_length:,} characters")
                    
                    if content_length > 0:
                        st.success("✅ Content successfully extracted and analyzed")
                    else:
                        st.warning("⚠️ Limited content extracted")
                    st.markdown("---")
    
    # Additional processed sources (not cited)
    if uncited_docs:
        st.markdown("### 📄 Additional Sources Analyzed")
        st.caption("Sources that were processed but not directly cited in the final report")
        
        # Show in a more compact format
        with st.expander(f"View {len(uncited_docs)} additional sources", expanded=False):
            for i, doc in enumerate(uncited_docs, 1):
                title = doc.get("title", "Untitled")
                url = doc.get("url", "")
                domain = doc.get("source_meta", {}).get("domain", "Unknown")
                content_length = len(doc.get("text", ""))
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{i}. {title}**")
                    st.write(f"🌐 {domain} | 🔗 [Link]({url})")
                with col2:
                    if content_length > 0:
                        st.success("✅ Processed")
                    else:
                        st.warning("❌ No content")
                
                if i < len(uncited_docs):  # Don't add separator after last item
                    st.markdown("---")


def _render_details_tab(results):
    """Render details tab with organized sections and consistent styling."""
    
    # Add custom CSS for consistent styling
    st.markdown("""
    <style>
    .details-section {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border-left: 4px solid #0066cc;
    }
    .details-title {
        font-size: 1.2em;
        font-weight: 600;
        color: #0066cc;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .details-subtitle {
        font-size: 1.1em;
        font-weight: 500;
        color: #333;
        margin: 15px 0 10px 0;
    }
    .details-content {
        font-size: 0.95em;
        line-height: 1.5;
    }
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 15px;
        margin: 15px 0;
    }
    .metric-item {
        text-align: center;
        padding: 10px;
        background: white;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
    }
    .metric-value {
        font-size: 1.4em;
        font-weight: 600;
        color: #0066cc;
    }
    .metric-label {
        font-size: 0.9em;
        color: #666;
        margin-top: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Section 1: Run Details
    st.markdown('<div class="details-section">', unsafe_allow_html=True)
    st.markdown('<div class="details-title">⚙️ Run Configuration</div>', unsafe_allow_html=True)
    
    # Get configuration details
    selected_model = getattr(st.session_state, 'selected_model_key', 'Unknown')
    model_config = Config.get_available_models_dict().get(selected_model, {})
    constraints = getattr(st.session_state, 'last_constraints', {})
    
    config_col1, config_col2 = st.columns(2)
    with config_col1:
        st.markdown("**Model Configuration:**")
        st.write(f"• **Model:** {selected_model}")
        if model_config:
            provider = model_config.get('provider', 'Unknown') if isinstance(model_config, dict) else getattr(model_config, 'provider', 'Unknown')
            st.write(f"• **Provider:** {provider}")
            model_id = model_config.get('model_id', 'Unknown') if isinstance(model_config, dict) else getattr(model_config, 'model_id', 'Unknown')
            if model_id != 'Unknown':
                st.write(f"• **Model ID:** {model_id}")
    
    with config_col2:
        st.markdown("**Research Settings:**")
        st.write(f"• **Max Rounds:** {constraints.get('max_rounds', 'Unknown')}")
        st.write(f"• **Per Domain Cap:** {constraints.get('per_domain_cap', 'Unknown')}")
        st.write(f"• **Timeout:** {constraints.get('fetch_timeout_s', 'Unknown')}s")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Section 2: Research Metrics Overview
    st.markdown('<div class="details-section">', unsafe_allow_html=True)
    st.markdown('<div class="details-title">📊 Research Metrics</div>', unsafe_allow_html=True)
    
    state = results.get("state", {})
    metrics = results.get("metrics", {})
    report = results.get("report", {})
    
    # Key metrics in a clean grid
    metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
    with metric_col1:
        st.metric("⏱️ Duration", f"{metrics.get('duration_s', 0):.1f}s")
    with metric_col2:
        st.metric("📚 Sources", metrics.get('sources_count', 0))
    with metric_col3:
        st.metric("📝 Claims", len(state.get('claims', [])))
    with metric_col4:
        st.metric("📄 Words", f"{report.get('word_count', 0):,}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Section 3: Model Benchmarks
    st.markdown('<div class="details-section">', unsafe_allow_html=True)
    st.markdown('<div class="details-title">🎯 Model Benchmarks</div>', unsafe_allow_html=True)
    _render_model_benchmarks()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Section 4: Detailed Analytics
    st.markdown('<div class="details-section">', unsafe_allow_html=True)
    st.markdown('<div class="details-title">📈 Detailed Analytics</div>', unsafe_allow_html=True)
    
    # Use tabs for different analysis views
    analysis_tab1, analysis_tab2, analysis_tab3 = st.tabs(["Pipeline Stats", "Claims Analysis", "Performance"])
    
    with analysis_tab1:
        st.markdown('<div class="details-subtitle">Pipeline Statistics</div>', unsafe_allow_html=True)
        
        pipeline_data = [
            ["Search Queries", len(state.get('queries', [])), "Search queries executed"],
            ["Search Results", len(state.get('search_results', [])), "Total search results found"],
            ["Documents Processed", len(state.get('documents', [])), "Documents successfully fetched"],
            ["Content Chunks", len(state.get('chunks', [])), "Text chunks analyzed"],
            ["Claims Verified", len(state.get('claims', [])), "Claims extracted and verified"],
            ["Citations Created", len(state.get('citations', [])), "Citations linked to claims"]
        ]
        
        # Clean table format
        for metric, value, description in pipeline_data:
            col1, col2, col3 = st.columns([3, 1, 4])
            col1.markdown(f"**{metric}**")
            col2.markdown(f"<span style='color: #0066cc; font-weight: 600; font-size: 1.1em;'>{value}</span>", unsafe_allow_html=True)
            col3.markdown(f"<span style='color: #666;'>{description}</span>", unsafe_allow_html=True)
    
    with analysis_tab2:
        st.markdown('<div class="details-subtitle">Claims Analysis</div>', unsafe_allow_html=True)
        
        claims = state.get('claims', [])
        if claims:
            # Calculate statistics
            claim_types = {}
            confidence_scores = []
            for claim in claims:
                claim_type = claim.get('type', 'unknown')
                claim_types[claim_type] = claim_types.get(claim_type, 0) + 1
                confidence_scores.append(claim.get('confidence', 0))
            
            # Display in organized format
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Distribution by Type**")
                for claim_type, count in sorted(claim_types.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count/len(claims)*100)
                    st.write(f"• **{claim_type.title()}:** {count} ({percentage:.1f}%)")
            
            with col2:
                st.markdown("**Confidence Metrics**")
                if confidence_scores:
                    avg_conf = sum(confidence_scores) / len(confidence_scores)
                    min_conf = min(confidence_scores)
                    max_conf = max(confidence_scores)
                    high_conf_count = sum(1 for c in confidence_scores if c > 0.7)
                    
                    st.metric("Average Confidence", f"{avg_conf:.2f}")
                    st.metric("High Confidence (>0.7)", high_conf_count)
        else:
            st.info("No claims data available")
    
    with analysis_tab3:
        st.markdown('<div class="details-subtitle">Performance Analysis</div>', unsafe_allow_html=True)
        
        duration = metrics.get('duration_s', 0)
        sources = metrics.get('sources_count', 0)
        claims_count = len(state.get('claims', []))
        
        if duration > 0:
            perf_data = [
                ["Sources per Second", f"{sources/duration:.2f}", "Fetching efficiency"],
                ["Claims per Source", f"{claims_count/max(sources, 1):.2f}", "Extraction rate"],
                ["Words per Second", f"{report.get('word_count', 0)/duration:.1f}", "Writing speed"]
            ]
            
            for metric, value, desc in perf_data:
                col1, col2, col3 = st.columns([3, 2, 4])
                col1.markdown(f"**{metric}**")
                col2.markdown(f"<span style='color: #0066cc; font-weight: 600;'>{value}</span>", unsafe_allow_html=True)
                col3.markdown(f"<span style='color: #666;'>{desc}</span>", unsafe_allow_html=True)
        else:
            st.info("Performance data not available")
    
    st.markdown('</div>', unsafe_allow_html=True)


def _render_results_section():
    """Legacy render results section - replaced by state-aware version."""
    pass


def _render_metrics_tab(results: Dict[str, Any]):
    """Render metrics tab with improved table-based layout."""
    st.markdown("### 📊 Research Metrics")
    
    state = results.get("state", {})
    metrics = results.get("metrics", {})
    report = results.get("report", {})
    
    # Compact overview metrics in a single row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("⏱️ Duration", f"{metrics.get('duration_s', 0):.1f}s")
    with col2:
        st.metric("📚 Sources", metrics.get('sources_count', 0))
    with col3:
        st.metric("📝 Claims", len(state.get('claims', [])))
    with col4:
        st.metric("📄 Words", f"{report.get('word_count', 0):,}")
    
    # Use tabs for different metric views
    metric_tab1, metric_tab2, metric_tab3 = st.tabs(["Pipeline Stats", "Claims Analysis", "Performance"])
    
    with metric_tab1:
        # Pipeline breakdown using Streamlit native components
        st.markdown("#### 🔄 Pipeline Statistics")
        
        pipeline_data = [
            ["Search Queries", len(state.get('queries', [])), "Number of search queries executed"],
            ["Search Results", len(state.get('search_results', [])), "Total search results found"],
            ["Documents Processed", len(state.get('documents', [])), "Documents successfully fetched"],
            ["Content Chunks", len(state.get('chunks', [])), "Text chunks analyzed"],
            ["Claims Verified", len(state.get('claims', [])), "Claims extracted and verified"],
            ["Citations Created", len(state.get('citations', [])), "Citations linked to claims"]
        ]
        
        # Use streamlit columns for better table display
        col_headers = st.columns([3, 1, 4])
        col_headers[0].markdown("**Metric**")
        col_headers[1].markdown("**Value**")
        col_headers[2].markdown("**Description**")
        
        st.markdown("---")
        
        for metric, value, description in pipeline_data:
            col_data = st.columns([3, 1, 4])
            col_data[0].markdown(f"**{metric}**")
            col_data[1].markdown(f"<span style='color: #0066cc; font-weight: 600; font-size: 1.1em;'>{value}</span>", unsafe_allow_html=True)
            col_data[2].markdown(f"<span style='color: #666;'>{description}</span>", unsafe_allow_html=True)
    
    with metric_tab2:
        # Claims analysis with better visualization
        claims = state.get('claims', [])
        if claims:
            st.markdown("#### 📝 Claims Breakdown")
            
            # Calculate statistics
            claim_types = {}
            confidence_scores = []
            for claim in claims:
                claim_type = claim.get('type', 'unknown')
                claim_types[claim_type] = claim_types.get(claim_type, 0) + 1
                confidence_scores.append(claim.get('confidence', 0))
            
            # Two-column layout for claim stats
            col1, col2 = st.columns(2)
            
            with col1:
                # Claims by type using Streamlit components
                st.markdown("**Distribution by Type**")
                type_data = [[t.title(), c, f"{(c/len(claims)*100):.1f}%"]
                            for t, c in sorted(claim_types.items(), key=lambda x: x[1], reverse=True)]
                
                # Headers
                header_cols = st.columns([2, 1, 1])
                header_cols[0].markdown("**Type**")
                header_cols[1].markdown("**Count**")
                header_cols[2].markdown("**%**")
                
                st.markdown("---")
                
                for type_name, count, percentage in type_data:
                    data_cols = st.columns([2, 1, 1])
                    data_cols[0].markdown(type_name)
                    data_cols[1].markdown(f"**{count}**")
                    data_cols[2].markdown(f"*{percentage}*")
            
            with col2:
                # Confidence statistics using Streamlit components
                st.markdown("**Confidence Metrics**")
                if confidence_scores:
                    avg_conf = sum(confidence_scores) / len(confidence_scores)
                    min_conf = min(confidence_scores)
                    max_conf = max(confidence_scores)
                    high_conf_count = sum(1 for c in confidence_scores if c > 0.7)
                    
                    # Use metrics for better display
                    metric_col1, metric_col2 = st.columns(2)
                    with metric_col1:
                        st.metric("Average", f"{avg_conf:.2f}")
                        st.metric("Minimum", f"{min_conf:.2f}")
                    with metric_col2:
                        st.metric("Maximum", f"{max_conf:.2f}")
                        st.metric("High Conf (>0.7)", high_conf_count)
        else:
            st.info("No claims data available")
    
    with metric_tab3:
        # Performance metrics
        st.markdown("#### ⚡ Performance Analysis")
        
        # Calculate performance metrics
        duration = metrics.get('duration_s', 0)
        sources = metrics.get('sources_count', 0)
        claims_count = len(state.get('claims', []))
        
        perf_data = []
        if duration > 0:
            perf_data.append(["Sources per Second", f"{sources/duration:.2f}", "Fetching efficiency"])
            perf_data.append(["Claims per Source", f"{claims_count/max(sources, 1):.2f}", "Extraction rate"])
            perf_data.append(["Words per Second", f"{report.get('word_count', 0)/duration:.1f}", "Writing speed"])
        
        if perf_data:
            # Headers using Streamlit columns
            header_cols = st.columns([3, 2, 4])
            header_cols[0].markdown("**Metric**")
            header_cols[1].markdown("**Value**")
            header_cols[2].markdown("**Description**")
            
            st.markdown("---")
            
            for metric, value, desc in perf_data:
                data_cols = st.columns([3, 2, 4])
                data_cols[0].markdown(f"**{metric}**")
                data_cols[1].markdown(f"<span style='color: #0066cc; font-weight: 600;'>{value}</span>", unsafe_allow_html=True)
                data_cols[2].markdown(f"<span style='color: #666;'>{desc}</span>", unsafe_allow_html=True)




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