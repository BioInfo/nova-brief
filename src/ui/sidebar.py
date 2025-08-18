"""Sidebar UI components for Nova Brief."""

import os
import streamlit as st
from typing import Dict, Any, Tuple
from src.config import Config
from src.storage.models import Constraints, create_default_constraints


def render_sidebar() -> Tuple[str, str, str, Constraints]:
    """Render the complete sidebar and return (selected_model, research_mode, target_audience, constraints)."""
    with st.sidebar:
        st.markdown("### ⚙️ Setup")
        
        # 1. Research Mode selection (primary control)
        selected_research_mode = _render_research_mode_selection()
        
        # 2. Research Settings (constraints driven by research mode)
        constraints = _render_research_mode_constraints(selected_research_mode)
        
        # 3. Target Audience selection
        target_audience = _render_target_audience_selection()
        
        # 4. Model selection with integrated API status
        selected_model = _render_model_selection_with_api_status()
        
        # Minimal about section
        st.markdown("---")
        st.caption("**Nova Brief** generates research reports with verified citations from multiple sources.")
    
    return selected_model, selected_research_mode, target_audience, constraints


def _render_research_mode_selection() -> str:
    """Render research mode selection with descriptions."""
    st.subheader("🎯 Research Mode")
    
    # Get available research modes
    research_modes = Config.get_research_modes()
    mode_names = list(research_modes.keys())
    
    # Initialize session state for research mode
    if 'selected_research_mode' not in st.session_state:
        st.session_state.selected_research_mode = Config.SELECTED_RESEARCH_MODE
    
    # Research mode selection
    selected_mode = st.selectbox(
        "Choose Research Approach:",
        options=mode_names,
        index=mode_names.index(st.session_state.selected_research_mode) if st.session_state.selected_research_mode in mode_names else 0,
        help="Select research depth and speed preference",
        key="research_mode_selectbox"
    )
    
    # Update session state
    if selected_mode != st.session_state.selected_research_mode:
        st.session_state.selected_research_mode = selected_mode
        st.rerun()
    
    # Show mode description
    mode_config = research_modes[selected_mode]
    st.info(f"**Goal:** {mode_config['goal']}")
    
    # Show mode settings in expandable section
    with st.expander("📋 Mode Details", expanded=False):
        settings = mode_config["settings"]
        st.write(f"**Target Length:** {settings['target_word_count']}")
        st.write(f"**Research Rounds:** {settings['max_rounds']}")
        st.write(f"**Sources per Domain:** {settings['per_domain_cap']}")
        st.write(f"**Strategy:** {settings['search_strategy'].title()}")
    
    return selected_mode


def _render_target_audience_selection() -> str:
    """Render target audience selection for Writer customization."""
    st.subheader("👥 Target Audience")
    
    audience_options = {
        "📊 Executive Summary": {
            "description": "High-level insights for decision makers",
            "style": "executive"
        },
        "🔬 Technical Report": {
            "description": "Detailed analysis for experts",
            "style": "technical"
        },
        "📰 General Audience": {
            "description": "Accessible overview for general readers",
            "style": "general"
        }
    }
    
    # Initialize session state
    if 'target_audience' not in st.session_state:
        st.session_state.target_audience = "📰 General Audience"
    
    audience_names = list(audience_options.keys())
    selected_audience = st.selectbox(
        "Choose Report Style:",
        options=audience_names,
        index=audience_names.index(st.session_state.target_audience) if st.session_state.target_audience in audience_names else 2,
        help="Select writing style and technical depth",
        key="audience_selectbox"
    )
    
    # Update session state
    if selected_audience != st.session_state.target_audience:
        st.session_state.target_audience = selected_audience
        st.rerun()
    
    # Show audience description
    audience_config = audience_options[selected_audience]
    st.caption(audience_config["description"])
    
    return selected_audience


def _render_research_mode_constraints(selected_research_mode: str) -> Constraints:
    """Render constraints form driven by research mode selection."""
    st.subheader("🎛️ Research Settings")
    
    # Get base constraints from research mode
    try:
        base_constraints = Config.apply_research_mode(selected_research_mode)
    except ValueError:
        # Fallback to default if mode not found
        st.warning(f"Unknown research mode: {selected_research_mode}")
        base_constraints = Config.apply_research_mode("⚖️ Balanced Analysis")
    
    # Show current mode settings
    st.success(f"**Mode:** {selected_research_mode}")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Rounds", base_constraints["max_rounds"])
    with col2:
        st.metric("Sources/Domain", base_constraints["per_domain_cap"])
    with col3:
        st.metric("Timeout", f"{base_constraints['fetch_timeout_s']:.0f}s")
    
    # Advanced settings override in expandable section
    with st.expander("⚙️ Advanced Overrides", expanded=False):
        st.caption("Override research mode defaults (optional)")
        
        # Allow manual overrides
        override_rounds = st.slider(
            "Override Max Rounds",
            min_value=1,
            max_value=8,
            value=base_constraints["max_rounds"],
            help="Override research mode default"
        )
        
        override_domain_cap = st.slider(
            "Override Sources per Domain",
            min_value=1,
            max_value=10,
            value=base_constraints["per_domain_cap"],
            help="Override research mode default"
        )
        
        override_timeout = st.slider(
            "Override Timeout (seconds)",
            min_value=5,
            max_value=30,
            value=int(base_constraints["fetch_timeout_s"]),
            help="Override research mode default"
        )
        
        # Domain filters
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
        
        # Apply overrides if different from defaults
        if (override_rounds != base_constraints["max_rounds"] or 
            override_domain_cap != base_constraints["per_domain_cap"] or
            override_timeout != base_constraints["fetch_timeout_s"]):
            st.info("⚠️ Using custom overrides instead of research mode defaults")
            base_constraints["max_rounds"] = override_rounds
            base_constraints["per_domain_cap"] = override_domain_cap
            base_constraints["fetch_timeout_s"] = float(override_timeout)
        
        # Parse domain filters
        include_domains = [d.strip() for d in include_domains_text.split('\n') if d.strip()] if include_domains_text else []
        exclude_domains = [d.strip() for d in exclude_domains_text.split('\n') if d.strip()] if exclude_domains_text else []
    
    # If expander wasn't used, set empty domain filters
    if 'include_domains' not in locals():
        include_domains = []
    if 'exclude_domains' not in locals():
        exclude_domains = []
    
    # Update constraints with domain filters
    base_constraints["include_domains"] = include_domains
    base_constraints["exclude_domains"] = exclude_domains
    
    # Convert to proper Constraints type
    constraints: Constraints = {
        "date_range": base_constraints.get("date_range"),
        "include_domains": include_domains,
        "exclude_domains": exclude_domains,
        "max_rounds": base_constraints["max_rounds"],
        "per_domain_cap": base_constraints["per_domain_cap"],
        "fetch_timeout_s": base_constraints["fetch_timeout_s"],
        "max_tokens_per_chunk": base_constraints.get("max_tokens_per_chunk", 1000)
    }
    
    return constraints


def _render_model_selection_with_api_status() -> str:
    """Render model selection with integrated API status."""
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
    
    # Show integrated API status and model details
    if selected_model_key in available_models_dict:
        model_config = available_models_dict[selected_model_key]
        
        # Integrated API status (compact)
        api_key = os.getenv(model_config.api_key_env)
        if api_key:
            st.success(f"✅ {model_config.api_key_env} configured")
        else:
            st.error(f"❌ {model_config.api_key_env} required")
            
            # Show setup instructions for missing API key
            if model_config.provider == "google":
                st.info("💡 [Get Google AI API key](https://aistudio.google.com/app/apikey)")
            elif model_config.provider == "anthropic":
                st.info("💡 [Get Anthropic API key](https://console.anthropic.com/)")
            elif model_config.provider == "openai":
                st.info("💡 [Get OpenAI API key](https://platform.openai.com/api-keys)")
            elif model_config.provider == "openrouter":
                st.info("💡 [Get OpenRouter API key](https://openrouter.ai/keys)")
            
            st.code(f"# Add to .env file:\n{model_config.api_key_env}=your_key_here")
        
        # Model details in compact format
        with st.expander("📋 Model Details", expanded=False):
            st.write(f"**Model ID:** `{model_config.model_id}`")
            st.write(f"**Provider:** {model_config.provider.title()}")
            if model_config.provider_params:
                st.write(f"**Parameters:** {model_config.provider_params}")
            if model_config.base_url:
                st.write(f"**Endpoint:** {model_config.base_url}")
            
            # Show partial key for verification if available
            if api_key:
                masked_key = f"{api_key[:8]}...{api_key[-4:]}"
                st.write(f"**API Key:** `{masked_key}`")
    
    return selected_model_key