"""
Nova Brief - Deep Research Agent
Main Streamlit application for running research briefs with citation tracking.
"""

import asyncio
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional
import streamlit as st
from dotenv import load_dotenv

# Import agent modules
from agent import planner, searcher, reader, analyst, verifier, writer
from observability.logging import get_logger, configure_logging
from observability.tracing import get_trace_events, clear_trace_events

# Load environment variables
load_dotenv()

# Configure logging and get logger
configure_logging()
logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="Nova Brief - Deep Research Agent",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .status-box {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .status-running {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
    }
    .status-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
    }
    .status-error {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize Streamlit session state variables."""
    if 'research_results' not in st.session_state:
        st.session_state.research_results = None
    if 'research_running' not in st.session_state:
        st.session_state.research_running = False
    if 'current_step' not in st.session_state:
        st.session_state.current_step = ""
    if 'step_results' not in st.session_state:
        st.session_state.step_results = {}
    if 'start_time' not in st.session_state:
        st.session_state.start_time = None


async def run_research_pipeline(topic: str, constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute the complete research pipeline.
    
    Args:
        topic: Research topic
        constraints: Optional research constraints
    
    Returns:
        Complete research results
    """
    results = {
        "topic": topic,
        "constraints": constraints or {},
        "start_time": time.time(),
        "steps": {},
        "success": False,
        "error": None
    }
    
    try:
        # Clear previous trace events
        clear_trace_events()
        
        # Step 1: Planning
        st.session_state.current_step = "🧠 Planning research approach..."
        logger.info(f"Starting research pipeline for topic: {topic}")
        
        plan_result = await planner.plan(topic, constraints)
        results["steps"]["planning"] = plan_result
        st.session_state.step_results["planning"] = plan_result
        
        if not plan_result["success"]:
            raise Exception(f"Planning failed: {plan_result.get('error', 'Unknown error')}")
        
        # Step 2: Searching
        st.session_state.current_step = "🔍 Executing search queries..."
        queries = plan_result["all_queries"]
        
        search_result = await searcher.search(queries)
        results["steps"]["searching"] = search_result
        st.session_state.step_results["searching"] = search_result
        
        if not search_result["success"]:
            raise Exception(f"Search failed: {search_result.get('error', 'Unknown error')}")
        
        # Step 3: Reading
        st.session_state.current_step = "📖 Fetching and processing content..."
        search_results = search_result["results"]
        
        read_result = await reader.read(search_results)
        results["steps"]["reading"] = read_result
        st.session_state.step_results["reading"] = read_result
        
        if not read_result["success"]:
            raise Exception(f"Reading failed: {read_result.get('error', 'Unknown error')}")
        
        # Step 4: Analysis
        st.session_state.current_step = "🔬 Analyzing content and extracting claims..."
        chunks = read_result["chunks"]
        
        analysis_result = await analyst.analyze(chunks, topic)
        results["steps"]["analysis"] = analysis_result
        st.session_state.step_results["analysis"] = analysis_result
        
        if not analysis_result["success"]:
            raise Exception(f"Analysis failed: {analysis_result.get('error', 'Unknown error')}")
        
        # Step 5: Verification
        st.session_state.current_step = "✅ Verifying claims and checking coverage..."
        
        verification_result = await verifier.verify(analysis_result)
        results["steps"]["verification"] = verification_result
        st.session_state.step_results["verification"] = verification_result
        
        if not verification_result["success"]:
            raise Exception(f"Verification failed: {verification_result.get('error', 'Unknown error')}")
        
        # Step 6: Writing
        st.session_state.current_step = "✍️ Generating final research brief..."
        documents = read_result["documents"]
        
        write_result = await writer.write(verification_result, analysis_result, documents)
        results["steps"]["writing"] = write_result
        st.session_state.step_results["writing"] = write_result
        
        if not write_result["success"]:
            raise Exception(f"Writing failed: {write_result.get('error', 'Unknown error')}")
        
        # Complete pipeline
        results["end_time"] = time.time()
        results["duration"] = results["end_time"] - results["start_time"]
        results["success"] = True
        
        # Store final report
        results["final_report"] = write_result["report_markdown"]
        results["metrics"] = write_result["metrics"]
        
        logger.info(f"Research pipeline completed successfully in {results['duration']:.1f}s")
        
        return results
        
    except Exception as e:
        results["end_time"] = time.time()
        results["duration"] = results["end_time"] - results["start_time"]
        results["error"] = str(e)
        results["success"] = False
        
        logger.error(f"Research pipeline failed: {e}")
        return results


def display_progress_status():
    """Display current progress status."""
    if st.session_state.research_running:
        st.markdown(f"""
        <div class="status-box status-running">
            <strong>🔄 Research in Progress</strong><br>
            {st.session_state.current_step}
        </div>
        """, unsafe_allow_html=True)
    elif st.session_state.research_results:
        if st.session_state.research_results["success"]:
            duration = st.session_state.research_results["duration"]
            st.markdown(f"""
            <div class="status-box status-success">
                <strong>✅ Research Completed</strong><br>
                Finished in {duration:.1f} seconds
            </div>
            """, unsafe_allow_html=True)
        else:
            error = st.session_state.research_results.get("error", "Unknown error")
            st.markdown(f"""
            <div class="status-box status-error">
                <strong>❌ Research Failed</strong><br>
                {error}
            </div>
            """, unsafe_allow_html=True)


def display_step_metrics():
    """Display metrics from completed steps."""
    if not st.session_state.step_results:
        return
    
    st.subheader("📊 Pipeline Metrics")
    
    cols = st.columns(3)
    
    # Planning metrics
    if "planning" in st.session_state.step_results:
        plan_data = st.session_state.step_results["planning"]
        with cols[0]:
            st.markdown("""
            <div class="metric-card">
                <h4>🧠 Planning</h4>
                <p><strong>Queries:</strong> {}</p>
                <p><strong>Sub-questions:</strong> {}</p>
            </div>
            """.format(
                plan_data.get("query_count", 0),
                len(plan_data.get("research_plan", {}).get("sub_questions", []))
            ), unsafe_allow_html=True)
    
    # Search metrics
    if "searching" in st.session_state.step_results:
        search_data = st.session_state.step_results["searching"]
        with cols[1]:
            metrics = search_data.get("metrics", {})
            st.markdown("""
            <div class="metric-card">
                <h4>🔍 Search</h4>
                <p><strong>Results:</strong> {}</p>
                <p><strong>Success Rate:</strong> {:.1%}</p>
            </div>
            """.format(
                metrics.get("total_unique_results", 0),
                metrics.get("successful_queries", 0) / max(metrics.get("total_queries", 1), 1)
            ), unsafe_allow_html=True)
    
    # Reading metrics
    if "reading" in st.session_state.step_results:
        read_data = st.session_state.step_results["reading"]
        with cols[2]:
            metrics = read_data.get("metrics", {})
            st.markdown("""
            <div class="metric-card">
                <h4>📖 Reading</h4>
                <p><strong>Documents:</strong> {}</p>
                <p><strong>Text Chunks:</strong> {}</p>
            </div>
            """.format(
                metrics.get("successful_fetches", 0),
                metrics.get("total_chunks", 0)
            ), unsafe_allow_html=True)
    
    # Analysis and verification metrics
    if "analysis" in st.session_state.step_results and "verification" in st.session_state.step_results:
        analysis_data = st.session_state.step_results["analysis"]
        verification_data = st.session_state.step_results["verification"]
        
        cols2 = st.columns(2)
        
        with cols2[0]:
            metrics = analysis_data.get("metrics", {})
            st.markdown("""
            <div class="metric-card">
                <h4>🔬 Analysis</h4>
                <p><strong>Claims:</strong> {}</p>
                <p><strong>Coverage:</strong> {:.1%}</p>
            </div>
            """.format(
                metrics.get("total_claims", 0),
                metrics.get("chunk_coverage", 0)
            ), unsafe_allow_html=True)
        
        with cols2[1]:
            metrics = verification_data.get("verification_metrics", {})
            st.markdown("""
            <div class="metric-card">
                <h4>✅ Verification</h4>
                <p><strong>Verified:</strong> {}</p>
                <p><strong>Score:</strong> {:.1%}</p>
            </div>
            """.format(
                metrics.get("verified_claims", 0),
                metrics.get("coverage_score", 0)
            ), unsafe_allow_html=True)


def display_research_results():
    """Display the final research results."""
    if not st.session_state.research_results or not st.session_state.research_results["success"]:
        return
    
    results = st.session_state.research_results
    
    st.subheader("📄 Research Brief")
    
    # Display the report
    report = results.get("final_report", "")
    if report:
        st.markdown(report)
        
        # Download button
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"research_brief_{timestamp}.md"
        
        st.download_button(
            label="📥 Download Research Brief",
            data=report,
            file_name=filename,
            mime="text/markdown"
        )
    
    # Show final metrics
    if "metrics" in results:
        st.subheader("📈 Final Metrics")
        metrics = results["metrics"]
        
        cols = st.columns(4)
        with cols[0]:
            st.metric("Word Count", metrics.get("word_count", 0))
        with cols[1]:
            st.metric("Citations", metrics.get("citation_count", 0))
        with cols[2]:
            st.metric("References", metrics.get("reference_count", 0))
        with cols[3]:
            st.metric("Coverage Score", f"{metrics.get('coverage_score', 0):.1%}")


def main():
    """Main Streamlit application."""
    initialize_session_state()
    
    # Header
    st.markdown('<h1 class="main-header">🔬 Nova Brief</h1>', unsafe_allow_html=True)
    st.markdown("*Deep Research Agent with Citation Tracking*")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Environment status
        api_key = os.getenv("CEREBRAS_API_KEY")
        if api_key:
            st.success("✅ Cerebras API configured")
        else:
            st.error("❌ CEREBRAS_API_KEY not set")
        
        st.markdown("---")
        
        # Research constraints
        st.subheader("🔧 Research Settings")
        max_rounds = st.slider("Max Search Rounds", 1, 5, 3)
        max_results = st.slider("Results per Query", 5, 20, 10)
        
        constraints = {
            "max_rounds": max_rounds,
            "max_results_per_query": max_results
        }
    
    # Main interface
    if not st.session_state.research_running:
        st.subheader("🎯 Research Topic")
        
        # Topic input
        topic = st.text_area(
            "Enter your research topic or question:",
            placeholder="e.g., Impact of artificial intelligence on healthcare diagnostics",
            height=100
        )
        
        # Example topics
        st.markdown("**Example topics:**")
        examples = [
            "Climate change impact on global food security",
            "Quantum computing applications in cryptography", 
            "Remote work effects on employee productivity",
            "CRISPR gene editing ethical considerations"
        ]
        
        cols = st.columns(2)
        for i, example in enumerate(examples):
            col = cols[i % 2]
            if col.button(example, key=f"example_{i}"):
                st.rerun()
        
        # Start research button
        if st.button("🚀 Start Research", disabled=not topic.strip(), type="primary"):
            if not api_key:
                st.error("Please set CEREBRAS_API_KEY in your environment")
                return
            
            st.session_state.research_running = True
            st.session_state.start_time = time.time()
            st.session_state.current_step = "Initializing research pipeline..."
            st.session_state.step_results = {}
            
            # Run the research pipeline
            with st.spinner("Running research pipeline..."):
                results = asyncio.run(run_research_pipeline(topic.strip(), constraints))
            
            st.session_state.research_results = results
            st.session_state.research_running = False
            st.session_state.current_step = ""
            
            st.rerun()
    
    # Display progress and results
    display_progress_status()
    display_step_metrics()
    display_research_results()
    
    # Footer
    st.markdown("---")
    st.markdown("*Powered by Cerebras GPT-OSS-120B • Built with Streamlit*")


if __name__ == "__main__":
    main()