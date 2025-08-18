"""Streamlit UI for Nova Brief research agent - Refactored version."""

import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Import UI components
from src.ui.sidebar import render_sidebar
from src.ui.main_panel import render_main_panel
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


def check_environment() -> bool:
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


def main():
    """Main Streamlit application."""
    init_session_state()
    
    # Check environment setup
    if not check_environment():
        st.error("⚠️ Environment not properly configured. Please set required API keys.")
        st.stop()
    
    # Render sidebar and get configuration
    selected_model, research_mode, target_audience, constraints = render_sidebar()
    
    # Render main panel with configuration
    render_main_panel(constraints, selected_model, target_audience)


if __name__ == "__main__":
    main()