"""Main panel UI components for Nova Brief."""

import asyncio
import time
from typing import Dict, Any
import streamlit as st
from datetime import datetime
from src.agent.orchestrator import run_research_pipeline, validate_pipeline_inputs
from src.storage.models import Constraints
from src.config import Config
from src.tools.eta import estimate_eta, format_eta
from src.observability.logging import get_logger

logger = get_logger(__name__)


def render_main_panel(constraints: Constraints, selected_model: str, target_audience: str):
    """Render state-aware main panel that adapts to current UI state."""
    
    # Determine current UI state
    ui_state = _get_ui_state()
    
    if ui_state == "ready":
        _render_ready_state(constraints, selected_model, target_audience)
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


def _render_ready_state(constraints: Constraints, selected_model: str, target_audience: str):
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
                st.session_state.target_audience = target_audience
                _run_research(topic, constraints, selected_model, target_audience)
    
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
        from .results import render_evidence_map_tab
        render_evidence_map_tab(results)
    
    with tab3:
        from .results import render_enhanced_sources_tab
        render_enhanced_sources_tab(results)
    
    with tab4:
        from .results import render_details_tab
        render_details_tab(results)
    
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


def _run_research(topic: str, constraints: Constraints, selected_model: str, target_audience: str):
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
            topic, constraints, selected_model, target_audience, callback
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


async def _run_research_with_monitoring(topic: str, constraints: Constraints, selected_model: str, target_audience: str, callback):
    """Run research pipeline with progress monitoring."""
    # Pass target_audience as part of constraints for now
    enhanced_constraints = dict(constraints)
    enhanced_constraints['_target_audience'] = target_audience
    
    # Now the orchestrator supports callbacks!
    return await run_research_pipeline(
        topic=topic,
        constraints=enhanced_constraints,
        selected_model=selected_model,
        progress_callback=callback.update_progress
    )