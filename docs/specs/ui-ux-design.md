# UI/UX Design Specification — Nova Brief Interface

2025-08-17 21:40:12 - Initial version. Defines the complete UI/UX redesign for Nova Brief Streamlit application based on user feedback and usability analysis.

References:
- PRD: [../prd.md](../prd.md)
- Master Plan: [../master-plan.md](../master-plan.md)
- Module Specs: [./module-specs.md](./module-specs.md)
- Current implementation: [../../src/app.py](../../src/app.py)
- UI/UX prompt: [../prompts/ui-ux.md](../prompts/ui-ux.md)

---

## 1) Design Objectives

**Problem Statement:**
The current Nova Brief UI suffers from:
- Overwhelming configuration options displayed simultaneously
- Poor visual hierarchy and inconsistent representation
- Non-functional research logs section
- Difficult-to-parse results display
- Cluttered sidebar with mixed concerns

**Design Goals:**
- Progressive disclosure to hide complexity by default
- Clear state-aware interface (Ready → Running → Results)
- Improved evidence discoverability through claims-to-sources mapping
- Live progress feedback with streaming logs
- Professional, clean aesthetic suitable for research professionals

---

## 2) Core Design Principles

### Progressive Disclosure
- Hide advanced options behind expanders by default
- Show only essential controls in primary interface
- Provide contextual help and tooltips for guidance

### Clarity and Guidance
- Clear labeling for all interface elements
- Contextual help text explaining configuration choices
- Visual indicators for system status and API readiness

### Visual Hierarchy & Consistency
- Consistent spacing and typography throughout
- Clear separation between configuration, input, progress, and results
- Strategic use of whitespace and dividers

### Stateful Design
Interface adapts to three distinct states:
1. **Ready State**: Clean input form with minimal configuration
2. **Running State**: Progress dashboard with live updates
3. **Results State**: Organized tabs for different result views

---

## 3) Layout Architecture

### 3.1 Sidebar (Configuration Panel)

**Simplified Structure:**
```
⚙️ Configuration
├── 🤖 Model Selection (Hierarchical)
│   ├── Provider Selection (Dropdown)
│   └── Model Selection (Dynamic based on provider)
├── 🎛️ Research Settings
│   ├── Max Research Rounds (Always visible)
│   └── ⚙️ Advanced Settings (Expandable)
│       ├── Results per Domain
│       ├── Fetch Timeout
│       └── Domain Filters
└── 🔑 API Status (Compact)
    └── View Details (Expandable)
```

**Key Improvements:**
- Hierarchical model selection reduces cognitive load
- Progressive disclosure for advanced settings
- Compact API status with expandable details
- Removed benchmarks from sidebar (moved to results)

### 3.2 Main Panel (State-Aware)

**Ready State Layout:**
```
┌─ Welcome Section ────────────────────────────┐
│ 🔍 Nova Brief - Deep Research Agent         │
│ Generate analyst-grade briefs with citations │
│ 💡 Enter a research topic to begin analysis │
└──────────────────────────────────────────────┘

┌─ Input Area (80%) ─────┬─ Status Panel (20%) ─┐
│ 🎯 Research Topic      │ 📊 System Status      │
│ [Large text area]      │ ⏳ Ready for Research │
│ [🚀 Start Research]    │ • Model: Claude 3.5   │
│                        │ • Rounds: 3           │
└────────────────────────┴───────────────────────┘
```

**Running State Layout:**
```
┌─ Progress Dashboard ─────────────────────────┐
│ 🔄 Research Active: [Topic Name]            │
│ ████████████░░░░░░░░ 65% Complete           │
│ 🔍 Step 3/6: Reading sources...             │
│ ⏱️ ETA: 2m 15s remaining                   │
└──────────────────────────────────────────────┘

┌─ Live Progress Logs ─────────────────────────┐
│ [12:34:56] ✅ Planning: Generated 4 queries │
│ [12:35:12] 🔍 Searching: Found 23 results  │
│ [12:35:45] 📖 Reading: Processing 8 sources │
│ [Live streaming continues...]               │
└──────────────────────────────────────────────┘
```

**Results State Layout:**
```
┌─ Research Complete ──────────────────────────┐
│ ✅ Research Complete: [Topic Name]          │
│ 📊 Sources: 12 | Claims: 45 | Duration: 3m │
└──────────────────────────────────────────────┘

┌─ Results Tabs ───────────────────────────────┐
│ [📄 Brief] [🗺️ Evidence Map] [🔗 Sources] [📊 Details] │
│                                              │
│ [Tab-specific content area]                  │
└──────────────────────────────────────────────┘
```

---

## 4) Component Specifications

### 4.1 Hierarchical Model Selection

**Implementation:**
- **Provider Selectbox**: Groups models by provider (OpenRouter, OpenAI, Anthropic, Google)
- **Model Selectbox**: Dynamically populated based on provider selection
- **Status Integration**: Real-time API key validation with visual indicators

**Provider Mapping:**
```python
PROVIDER_GROUPS = {
    "openrouter": {
        "display": "🔗 OpenRouter",
        "models": ["gpt-oss-120b", "claude-sonnet-4", "gemini-2.5-flash", ...]
    },
    "openai": {
        "display": "🤖 OpenAI Direct", 
        "models": ["gpt-5-mini-direct"]
    },
    "anthropic": {
        "display": "🧠 Anthropic Direct",
        "models": ["claude-sonnet-4-direct"]
    },
    "google": {
        "display": "🔍 Google Direct",
        "models": ["gemini-2.5-flash-direct", "gemini-2.5-pro-direct"]
    }
}
```

### 4.2 Enhanced Results Tabs

**📄 Brief Tab:**
- Clean markdown rendering of final report
- Proper citation formatting
- Professional layout with good typography

**🗺️ Evidence Map Tab (NEW FEATURE):**
```
┌─ Claims (40%) ──────────┬─ Sources (60%) ─────────┐
│ 📝 Extracted Claims     │ 📚 Supporting Evidence  │
│                         │                         │
│ ☑️ Claim 1: AI adoption │ ▼ Source 1: [Title]    │
│ ☑️ Claim 2: Cost impact │   "AI adoption increased│
│ ☑️ Claim 3: Healthcare  │    by 300% in 2024..." │
│                         │                         │
│ [Interactive selection] │ ▼ Source 2: [Title]    │
│                         │   "Supporting text..."  │
└─────────────────────────┴─────────────────────────┘
```

**🔗 Sources Tab:**
- Clean list of all unique source URLs
- Organized by domain/type
- Quick access links and metadata

**📊 Details & Benchmarks Tab:**
- Run configuration details (model, constraints used)
- Performance benchmarks (moved from sidebar)
- Pipeline metrics and breakdown
- Historical performance data

### 4.3 Live Logging System

**Implementation Strategy:**
```python
class StreamlitLogHandler(logging.Handler):
    """Custom logging handler for real-time log streaming."""
    
    def emit(self, record):
        log_entry = {
            'timestamp': record.created,
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module
        }
        
        # Thread-safe append to session state
        if 'live_logs' not in st.session_state:
            st.session_state.live_logs = []
        st.session_state.live_logs.append(log_entry)
```

**Progress Callback Integration:**
- Real-time updates via orchestrator progress callbacks
- Throttled UI updates (max 2Hz) to prevent performance issues
- ETA calculation based on current progress and historical data

---

## 5) State Management

### 5.1 UI State Tracking

**State Enum:**
```python
class UIState(Enum):
    READY = "ready"
    RUNNING = "running" 
    RESULTS = "results"
```

**State Transitions:**
- READY → RUNNING: When "Start Research" clicked
- RUNNING → RESULTS: When research completes successfully
- RUNNING → READY: When research fails or is cancelled
- RESULTS → READY: When new research is initiated

### 5.2 Session State Management

**Key Session Variables:**
```python
st.session_state = {
    'ui_state': UIState.READY,
    'research_results': None,
    'research_running': False,
    'live_logs': [],
    'research_state': None,
    'research_start_time': None,
    'selected_provider': 'openrouter',
    'selected_model': 'gpt-oss-120b-openrouter-cerebras'
}
```

---

## 6) Implementation Plan

### 6.1 Priority 1: Core Layout Restructuring

**Target Functions:**
- `main()`: State-aware layout switching
- `_render_hierarchical_model_selection()`: New two-tier selection
- `_render_progressive_constraints()`: Advanced settings in expander
- `_render_compact_api_status()`: Simplified status display

### 6.2 Priority 2: Enhanced Progress Tracking

**Target Functions:**
- `StreamlitLogHandler`: Custom logging handler
- `_render_progress_dashboard()`: Dynamic progress interface
- `_render_live_logs()`: Real-time log streaming
- Progress callback integration with orchestrator

### 6.3 Priority 3: Results Enhancement

**Target Functions:**
- `_render_evidence_map_tab()`: Claims-to-sources mapping
- `_render_details_tab()`: Configuration and benchmarks
- `_render_enhanced_sources()`: Improved source presentation
- Tab organization and navigation

### 6.4 Priority 4: Polish and Integration

**Target Functions:**
- State transition management
- Error handling and recovery
- Performance optimization
- Accessibility improvements

---

## 7) Technical Requirements

### 7.1 Dependencies

**Existing (No changes required):**
- streamlit
- Standard library (logging, time, datetime)
- Existing Nova Brief modules

**Enhancements:**
- Enhanced session state management
- Custom logging handlers
- Improved component organization

### 7.2 Performance Considerations

**Optimization Strategies:**
- Throttled progress updates (0.5s minimum interval)
- Efficient log streaming with circular buffer
- Lazy loading of heavy components
- Minimal re-rendering through careful state management

### 7.3 Accessibility

**Requirements:**
- Clear visual hierarchy with proper heading structure
- Adequate color contrast ratios
- Keyboard navigation support
- Screen reader compatible labels and descriptions

---

## 8) Testing Strategy

### 8.1 Usability Testing

**Test Scenarios:**
1. New user onboarding flow
2. Configuration of different model/provider combinations
3. Research execution with progress monitoring
4. Results exploration and evidence mapping
5. Error handling and recovery scenarios

### 8.2 Performance Testing

**Metrics:**
- UI responsiveness during research execution
- Log streaming performance with high message volume
- Memory usage with large result sets
- State transition timing

### 8.3 Compatibility Testing

**Browsers:**
- Chrome, Firefox, Safari, Edge (latest versions)
- Mobile responsiveness (basic validation)

---

## 9) Migration Strategy

### 9.1 Backward Compatibility

**Preserved Features:**
- All existing functionality maintained
- Configuration compatibility with existing setups
- Session state migration for in-progress research

### 9.2 Gradual Rollout

**Implementation Phases:**
1. Core layout restructuring (sidebar + main panel)
2. Enhanced progress tracking and logging
3. Results enhancement with Evidence Map
4. Polish, optimization, and testing

---

## 10) Success Metrics

### 10.1 User Experience Metrics

**Qualitative:**
- Reduced time to first successful research run
- Improved discoverability of key features
- Enhanced understanding of research progress
- Better evidence-to-claim connection

**Quantitative:**
- Reduced configuration errors
- Increased feature utilization
- Improved task completion rates
- Decreased support requests

### 10.2 Technical Metrics

**Performance:**
- UI responsiveness maintained during research
- Memory usage within acceptable bounds
- Log streaming without dropped messages
- State transitions without errors

---

## 11) Future Enhancements

### 11.1 Planned Improvements

**Stage 2+:**
- Advanced filtering and search in Evidence Map
- Export functionality for different formats
- Collaborative features for shared research
- Advanced analytics and reporting

### 11.2 Accessibility Enhancements

**Future Considerations:**
- High contrast theme option
- Font size adjustment controls
- Enhanced keyboard navigation
- Screen reader optimization

---

## 12) Change Control

Any modifications to this UI/UX specification:
- Update this document with rationale
- Update implementation in [../../src/app.py](../../src/app.py)
- Record decision in Memory Bank: [../../memory-bank/decisionLog.md](../../memory-bank/decisionLog.md)
- Test affected functionality across all supported scenarios

---

## 13) Implementation Checklist

MVP Implementation Tasks:
- [ ] Hierarchical model selection system
- [ ] Progressive disclosure for research settings  
- [ ] Compact API status indicators
- [ ] State-aware main panel layout
- [ ] Live progress tracking with ETA
- [ ] Real-time log streaming
- [ ] Evidence Map tab implementation
- [ ] Enhanced results organization
- [ ] State transition management
- [ ] Error handling and recovery
- [ ] Performance optimization
- [ ] Documentation updates