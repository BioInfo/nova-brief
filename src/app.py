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
from src.agent import planner, searcher, reader, analyst, verifier, writer
from src.observability.logging import get_logger, configure_logging
from src.observability.tracing import get_trace_events, clear_trace_events

# Load environment variables from both .env and .env.local
load_dotenv()  # Load .env
load_dotenv('.env.local')  # Load .env.local (overrides .env if present)

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

# Modern CSS with professional UI/UX design
st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Vector icon system using SVG */
    .icon-research {
        width: 24px;
        height: 24px;
        background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/></svg>') no-repeat center;
        background-size: contain;
        display: inline-block;
        margin-right: 12px;
    }
    
    .icon-settings {
        width: 20px;
        height: 20px;
        background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>') no-repeat center;
        background-size: contain;
        display: inline-block;
        margin-right: 8px;
        vertical-align: middle;
    }
    
    .icon-ai {
        width: 20px;
        height: 20px;
        background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>') no-repeat center;
        background-size: contain;
        display: inline-block;
        margin-right: 8px;
        vertical-align: middle;
    }
    
    /* Main header styling with gradient */
    .main-header {
        font-size: 3rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
        text-align: center;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1rem;
    }
    
    .subtitle {
        text-align: center;
        color: #64748b;
        font-size: 1.125rem;
        margin-bottom: 3rem;
        font-weight: 400;
        letter-spacing: 0.025em;
    }
    
    /* Modern sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
        border-right: 1px solid #e2e8f0;
    }
    
    /* Success/Status messages */
    .success-message {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        padding: 1.25rem;
        border-radius: 12px;
        margin: 1.5rem 0;
        font-weight: 500;
        box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.25);
    }
    
    /* Modern config sections - no ugly white boxes */
    .config-section {
        background: linear-gradient(135deg, rgba(255,255,255,0.8) 0%, rgba(248,250,252,0.9) 100%);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(226, 232, 240, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1.25rem 0;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    .config-section h3 {
        color: #1e293b;
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
    }
    
    .config-section h4 {
        color: #475569;
        font-weight: 600;
        font-size: 1rem;
        margin-bottom: 0.75rem;
        display: flex;
        align-items: center;
    }
    
    /* Topic input styling */
    .stTextArea textarea {
        border-radius: 12px;
        border: 2px solid #e2e8f0;
        font-size: 1rem;
        padding: 1.25rem;
        background: #ffffff;
        color: #1f2937 !important;
        transition: all 0.2s ease;
    }
    
    .stTextArea textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1);
        color: #1f2937 !important;
    }
    
    .stTextArea textarea::placeholder {
        color: #9ca3af !important;
    }
    
    /* Example topics - 4 horizontal bars */
    .topic-bar-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1rem;
        margin: 1.5rem 0 2rem 0;
    }
    
    .topic-bar {
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 1rem;
        cursor: pointer;
        transition: all 0.3s ease;
        text-align: center;
        font-size: 0.875rem;
        font-weight: 500;
        color: #475569;
        min-height: 60px;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
    }
    
    .topic-bar:hover {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.25);
        border-color: transparent;
    }
    
    /* Prominent start button */
    .start-button-container {
        margin: 3rem 0;
        text-align: center;
    }
    
    .start-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 1rem 3rem;
        font-size: 1.125rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        min-width: 200px;
    }
    
    .start-button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.5);
    }
    
    .start-button:disabled {
        background: #94a3b8;
        cursor: not-allowed;
        transform: none;
        box-shadow: none;
    }
    
    /* Pipeline metrics cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(248,250,252,0.95) 100%);
        border: 1px solid rgba(226, 232, 240, 0.5);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        margin: 0.75rem 0;
        backdrop-filter: blur(10px);
    }
    
    .metric-card h4 {
        color: #1f2937;
        margin-bottom: 1rem;
        font-size: 1rem;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .metric-card p {
        margin: 0.5rem 0;
        color: #6b7280;
        font-size: 0.9rem;
        line-height: 1.5;
    }
    
    /* Status indicators */
    .status-success {
        color: #059669;
        background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
        padding: 0.75rem 1.25rem;
        border-radius: 8px;
        font-size: 0.9rem;
        border: 1px solid #a7f3d0;
        font-weight: 500;
        margin: 0.5rem 0;
    }
    
    .status-error {
        color: #dc2626;
        background: linear-gradient(135deg, #fef2f2 0%, #fecaca 100%);
        padding: 0.75rem 1.25rem;
        border-radius: 8px;
        font-size: 0.9rem;
        border: 1px solid #fca5a5;
        font-weight: 500;
        margin: 0.5rem 0;
    }
    
    /* Remove ugly default button styling */
    .stButton > button {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        color: inherit !important;
        width: 100% !important;
        height: auto !important;
    }
    
    /* Typography improvements */
    h1, h2, h3 {
        letter-spacing: -0.025em;
    }
    
    /* Responsive grid for smaller screens */
    @media (max-width: 768px) {
        .topic-bar-container {
            grid-template-columns: repeat(2, 1fr);
        }
        
        .main-header {
            font-size: 2.5rem;
        }
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
    if 'selected_topic' not in st.session_state:
        st.session_state.selected_topic = ""


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
    """Display current progress status with clean styling."""
    if st.session_state.research_running:
        # Center align the progress status to match the button
        st.markdown('<div class="start-button-container">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            st.markdown("### Research in Progress")
            with st.spinner(st.session_state.current_step):
                st.empty()
        st.markdown('</div>', unsafe_allow_html=True)
    elif st.session_state.research_results:
        if st.session_state.research_results["success"]:
            duration = st.session_state.research_results["duration"]
            st.markdown(f"""
            <div class="success-message">
                <strong>Research Completed Successfully!</strong><br>
                Finished in {duration:.1f} seconds
            </div>
            """, unsafe_allow_html=True)
        else:
            error = st.session_state.research_results.get("error", "Unknown error")
            st.error(f"**Research Failed**\n\n{error}")
            
            # Show more detailed error information if available
            if "steps" in st.session_state.research_results:
                with st.expander("View Detailed Error Information"):
                    for step_name, step_data in st.session_state.research_results["steps"].items():
                        if not step_data.get("success", True):
                            st.write(f"**{step_name.title()} Error:**")
                            st.code(step_data.get("error", "No error details"))


def display_step_metrics():
    """Display metrics from completed steps."""
    if not st.session_state.step_results:
        return
    
    st.subheader("Pipeline Metrics")
    
    cols = st.columns(3)
    
    # Planning metrics
    if "planning" in st.session_state.step_results:
        plan_data = st.session_state.step_results["planning"]
        with cols[0]:
            st.markdown("""
            <div class="metric-card">
                <h4><span class="icon-vector"></span>Planning</h4>
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
                <h4><span class="icon-vector"></span>Search</h4>
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
                <h4><span class="icon-vector"></span>Reading</h4>
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
                <h4><span class="icon-vector"></span>Analysis</h4>
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
                <h4><span class="icon-vector"></span>Verification</h4>
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
    
    st.subheader("Research Brief")
    
    # Display the report
    report = results.get("final_report", "")
    if report:
        st.markdown(report)
        
        # Download button
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"research_brief_{timestamp}.md"
        
        st.download_button(
            label="Download Research Brief",
            data=report,
            file_name=filename,
            mime="text/markdown"
        )
    
    # Show final metrics
    if "metrics" in results:
        st.subheader("Final Metrics")
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
    
    # Header with proper vector icon
    st.markdown("""
    <h1 class="main-header">
        <span class="icon-research"></span>
        Nova Brief
    </h1>
    """, unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Deep Research Agent with Citation Tracking</p>', unsafe_allow_html=True)
    
    # Modern sidebar configuration
    with st.sidebar:
        st.markdown("""
        <div class="config-section">
            <h3><span class="icon-settings"></span>Configuration</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Environment status
        api_key = os.getenv("CEREBRAS_API_KEY")
        if api_key:
            st.markdown('<div class="status-success">Cerebras API configured</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-error">CEREBRAS_API_KEY not set</div>', unsafe_allow_html=True)
        
        # Research constraints with modern styling
        st.markdown("""
        <div class="config-section">
            <h4><span class="icon-settings"></span>Research Settings</h4>
        </div>
        """, unsafe_allow_html=True)
        
        max_rounds = st.slider("Max Search Rounds", 1, 5, 3, help="Number of search iterations")
        max_results = st.slider("Results per Query", 5, 20, 10, help="Sources per search query")
        
        constraints = {
            "max_rounds": max_rounds,
            "max_results_per_query": max_results
        }
        
        # AI Model info with proper styling
        st.markdown("""
        <div class="config-section">
            <h4><span class="icon-ai"></span>AI Model</h4>
            <p style="color: #64748b; font-size: 0.95rem; margin: 0.5rem 0;">Cerebras GPT-OSS-120B</p>
            <p style="color: #94a3b8; font-size: 0.85rem; margin: 0;">Optimized for research tasks</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Main interface
    if not st.session_state.research_running:
        st.markdown("### Research Topic")
        
        # Topic input with modern styling
        topic = st.text_area(
            "Enter your research topic or question:",
            value=st.session_state.selected_topic,
            placeholder="e.g., Impact of artificial intelligence on healthcare diagnostics",
            height=120,
            help="Describe what you want to research. Be specific for better results."
        )
        
        # Update session state when topic changes
        if topic != st.session_state.selected_topic:
            st.session_state.selected_topic = topic
        
        # Example topics - 4 horizontal bars
        st.markdown("### Example Topics")
        st.markdown("*Click any example to use it as your research topic*")
        
        examples = [
            "Climate change impact on global food security",
            "Quantum computing applications in cryptography",
            "Remote work effects on employee productivity",
            "CRISPR gene editing ethical considerations"
        ]
        
        # Create 4 horizontal topic bars
        st.markdown('<div class="topic-bar-container">', unsafe_allow_html=True)
        
        cols = st.columns(4)
        for i, example in enumerate(examples):
            with cols[i]:
                if st.button(example, key=f"example_{i}", use_container_width=True):
                    st.session_state.selected_topic = example
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Prominent start research button
        st.markdown('<div class="start-button-container">', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            # Create custom styled button using HTML since Streamlit buttons are limited
            button_disabled = "disabled" if not topic.strip() else ""
            button_class = "start-button" if topic.strip() else "start-button"
            
            if topic.strip():
                if st.button("🚀 Start Research", key="start_research", use_container_width=True, type="primary"):
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
            else:
                st.markdown("""
                <button class="start-button" disabled>
                    🚀 Start Research
                </button>
                """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Display progress and results
    display_progress_status()
    display_step_metrics()
    display_research_results()
    
    # Footer
    st.markdown("---")
    st.markdown("*Powered by Cerebras GPT-OSS-120B • Built with Streamlit*")


if __name__ == "__main__":
    main()