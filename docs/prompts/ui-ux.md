Prompt for UI/UX Design & Frontend Agent: Overhauling the Nova Brief Interface
Role: You are a UI/UX Design and Frontend Development Agent specializing in creating clean, intuitive, and professional data applications with Streamlit.

Objective: Your task is to redesign the Nova Brief Streamlit application interface based on direct user feedback. The current UI is considered cluttered, confusing, and visually unappealing. Your goal is to create a design and implementation plan that drastically improves usability, clarity, and aesthetics, transforming it into a polished, professional tool.

You must address all the issues raised: overwhelming configuration, inconsistent representation, poor whitespace and alignment, a non-functional "Research Logs" section, and a results display that is difficult to parse.

Part 1: Core Design Principles
Before generating implementation details, your redesign must adhere to these core principles:

Progressive Disclosure: Hide complexity by default. The user should only see what is necessary for the current step. Advanced options should be available but not intrusive.

Clarity and Guidance: Every element should be clearly labeled. Use tooltips and helper text to explain why a user might change a setting.

Visual Hierarchy & Consistency: Use layout, whitespace, dividers, and consistent styling to guide the user’s attention to the most important elements.

Stateful Design: The interface must clearly reflect the application's current state: 1. Ready for Input, 2. Research in Progress, and 3. Results Ready.

Part 2: Detailed Redesign Instructions (Component by Component)
Based on the provided screenshots and feedback, you will generate a detailed plan for the following components.

A. The Left Sidebar (Configuration Panel)

The current sidebar is overloaded. Your plan must declutter it significantly.

Model Selection:

Problem: The flat dropdown list is long and unorganized.

Solution: Redesign the model selection into a hierarchical system. Group the 12+ models by Provider (e.g., OpenRouter, Google, Anthropic, OpenAI). Use st.selectbox for the provider, which then dynamically populates a second st.selectbox with the models for that provider. Add visual cues (e.g., 🧠 Cerebras-Optimized) to the model names for clarity.

Research Settings:

Problem: All settings are visible at once, creating clutter.

Solution: Apply progressive disclosure. Place the most important setting, "Max Research Rounds," at the top. Group the less-frequently changed settings ("Results per Domain," "Fetch Timeout") inside an st.expander titled "⚙️ Advanced Settings," which is collapsed by default.

Status & Benchmark Panels:

Problem: The "API Status" and "Model Benchmarks" panels are status indicators, not user configurations, and they take up valuable space.

Solution:

Make the "API Status" more compact. Use a single st.success() or st.error() message.

Move the "Model Benchmarks" panel out of the sidebar entirely. This data is part of the results, not the setup. It should be a dedicated tab in the main panel once a research run is complete.

B. The Main Panel (Research & Results)

The main area needs better layout, state management, and a complete overhaul of the results display.

Initial "Ready" State:

Problem: Poor alignment and whitespace.

Solution: Use st.columns to create a more balanced layout. The "Research Topic" input area should be in a wider central column. The "Status" panel should be in a narrower side column. Add a welcome message or brief instructions below the title to guide new users.

"Research in Progress" State:

Problem: The UI is static during a run, and the logs are empty.

Solution: When research starts, the input form should be replaced by a dynamic progress view. This view must include:

A real-time progress bar and status text (e.g., "Step 3/6: Reading sources...").

A live-streaming log output area. The "Research Logs" bug must be fixed. Devise a plan to capture log output during the agent run (e.g., using a custom logging handler that writes to st.session_state) and display it here.

"Results Ready" State:

Problem: Displaying the final report as a single block of Markdown is overwhelming.

Solution: Redesign the results view using st.tabs for clear segmentation and reduced cognitive load.

📄 Brief Tab (Default): Display the polished, final report in a clean, readable format.

🗺️ Evidence Map Tab: This is a crucial new feature. Create a two-column layout (st.columns). The left column lists the extracted Claims. The right column lists the Sources with st.expander elements that reveal the text snippets supporting those claims. This directly addresses the difficulty of connecting claims to evidence.

🔗 Sources Tab: A simple, clean list of all unique source URLs found during the research, with links.

📊 Run Details & Benchmarks Tab: Display the configuration that was used for this specific run (model, constraints, etc.) and move the "Model Benchmarks" panel here from the sidebar.

Part 3: Final Output
Your final output must be a comprehensive plan for the Coding Agent, consisting of two parts:

A Design Mockup/Wireframe Description:

Provide a textual description of the new, clean layout. Describe the sidebar and the three states of the main panel (Ready, Running, Results) in detail.

A Streamlit Implementation Plan:

Provide a bulleted list of actionable changes for the Coding Agent. For each change, specify the target file (primarily src/app.py), the Streamlit components to use (e.g., "Replace model selection st.selectbox with two chained st.selectbox widgets for Provider and Model"), and the logic required to implement the new design. Include a specific plan to fix the empty "Research Logs" issue.