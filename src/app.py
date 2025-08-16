"""Streamlit UI for Nova Brief research agent."""

import os
import asyncio
from typing import Dict, Any, Optional
import streamlit as st
from datetime import datetime
import json
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Import agent components
from src.agent.orchestrator import run_research_pipeline, validate_pipeline_inputs
from src.storage.models import create_default_constraints, Constraints
from src.observability.logging import get_logger

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
        
        # Research constraints
        constraints = _render_constraints_form()
        
        # API Configuration status
        st.subheader("🔑 API Status")
        _render_api_status()
        
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
                    _run_research(topic, constraints)
        
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


def _render_api_status():
    """Render API configuration status."""
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    
    if openrouter_key:
        st.success("✅ OpenRouter API Key")
        # Show partial key for verification
        masked_key = f"{openrouter_key[:8]}...{openrouter_key[-4:]}"
        st.code(masked_key)
    else:
        st.error("❌ OpenRouter API Key Missing")
    
    # Show model configuration
    model = os.getenv("MODEL", "openai/gpt-oss-120b")
    st.info(f"🤖 Model: {model}")


def _render_status_panel():
    """Render research status panel."""
    if st.session_state.research_running:
        st.info("🔄 Research Active")
        
        # Show progress indicator
        progress_placeholder = st.empty()
        with progress_placeholder:
            st.progress(0.5)  # Indeterminate progress
        
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


def _run_research(topic: str, constraints: Constraints):
    """Execute research pipeline asynchronously."""
    st.session_state.research_running = True
    st.session_state.research_logs = []
    
    # Create progress indicators
    progress_container = st.container()
    
    with progress_container:
        st.info("🚀 Starting research pipeline...")
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    try:
        # Run research pipeline
        with st.spinner("Conducting research..."):
            # Since Streamlit doesn't handle async well, we'll use asyncio.run
            results = asyncio.run(run_research_pipeline(topic, constraints))
        
        # Store results
        st.session_state.research_results = results
        st.session_state.research_running = False
        
        # Clear progress indicators
        progress_bar.progress(1.0)
        status_text.success("✅ Research completed!")
        
        # Force rerun to update UI
        st.rerun()
        
    except Exception as e:
        st.session_state.research_running = False
        st.session_state.research_results = {
            "success": False,
            "error": str(e),
            "state": None,
            "report": None
        }
        
        # Show error
        progress_container.error(f"❌ Research failed: {str(e)}")
        
        logger.error(f"Research failed in UI: {e}")


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
                    st.text_area("Content Preview", snippet, height=100, disabled=True)


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