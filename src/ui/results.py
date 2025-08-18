"""Results UI components for Nova Brief."""

import streamlit as st
from typing import Dict, Any
from datetime import datetime
from src.config import Config
from src.tools.eta import get_latest_eval_results


def render_evidence_map_tab(results):
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
        
        # Display claims for current page
        for page_idx, claim in enumerate(current_page_claims):
            actual_idx = start_idx + page_idx
            claim_id = claim.get("id", f"claim_{actual_idx}")
            claim_text = claim.get("text", "Unknown claim")
            confidence = claim.get("confidence", 0)
            claim_type = claim.get("type", "unknown")
            
            # Determine confidence level for styling
            if confidence > 0.7:
                conf_icon = "✅"
            elif confidence > 0.4:
                conf_icon = "⚠️"
            else:
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
                st.markdown(f"<span>{conf_icon}</span>", unsafe_allow_html=True)
            
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


def render_enhanced_sources_tab(results):
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


def render_details_tab(results):
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


def _render_model_benchmarks():
    """Render model benchmarks section."""
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