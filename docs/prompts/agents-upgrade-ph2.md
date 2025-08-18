Of course. Here is a comprehensive, single-source prompt that synthesizes all of your recent ideas. It combines the "Phase 2" agent upgrades with the "Heterogeneous Agent Policies" concept into a unified vision.

This prompt is designed to be fed directly to a capable coding and architecture agent (like Roo Code Agent) to generate the necessary documentation updates and implementation plan.

-----

### **Master Prompt for Roo Code Agent: Implementing "Phase 2 Agent Intelligence" for Nova Brief**

**Role:** You are the Lead Architect and Implementation Agent for the Nova Brief project.

**Objective:** Your mission is to evolve Nova Brief from a smart, single-pipeline tool into a truly strategic, multi-agent research platform. You will implement **"Phase 2 Agent Intelligence,"** a major architectural upgrade centered on two core, interconnected concepts:

1.  **Heterogeneous Agent Policies:** The system will use different, specialized LLMs for each agent (Planner, Analyst, etc.) within a single run, based on a user-selected policy (e.g., "Thrifty," "Quality-First").
2.  **Advanced Agent Capabilities:** Each agent's core function will be upgraded to perform more sophisticated, expert-level tasks.

You are to update all project documentation to reflect this new vision and provide a detailed, file-by-file implementation plan.

-----

#### **Part 1: The New Architecture - Strategic, Heterogeneous Orchestration**

The fundamental change is moving from a simple, linear pipeline to a dynamic "team of specialists." The user will no longer select a single model; they will select a **Research Policy**. This policy dictates which model (the "specialist") is assigned to each agent, allowing us to use powerful, expensive models only for the most critical reasoning tasks, while using faster, cheaper models for more structured steps.

The advanced agent capabilities (like dynamic planning and context-aware analysis) are the *expert tasks* that these specialized models will perform.

-----

#### **Part 2: Detailed Implementation Plan**

**1. Implement the "Research Policies" Configuration System**

  * **File:** `src/config.py`
  * **Action:** Define the `AGENT_POLICIES` data structure. This will be the central truth for model-to-agent mapping. Include policies for "Balanced," "Thrifty," "Quality-First," and "Cerebras-Optimized."
  * **Example Structure:**
    ```python
    AGENT_POLICIES = {
        "Quality-First (Maximizes Insight)": {
            "planner": "claude-sonnet-4-openrouter-default", // Creative strategy
            "analyst": "qwen3-235b-openrouter-default",   // Deepest reasoning for synthesis
            "writer": "qwen3-235b-openrouter-default",    // Polished, sophisticated language
            "critic": "claude-sonnet-4-openrouter-default"     // Strong editorial review
        },
        "Thrifty (Cost-Optimized)": {
            "planner": "gemini-2.5-flash-direct", // Cheap and fast for planning
            "analyst": "claude-sonnet-4-direct", // Capable but cost-effective analysis
            "writer": "claude-sonnet-4-direct",  // Good quality writing
            "critic": "gemini-2.5-flash-direct"    // Quick, final check
        },
        // ... add other policies
    }
    ```

**2. Redesign the UI for Policy-Based Research**

  * **File:** `src/app.py`
  * **Action:** Overhaul the configuration sidebar.
    1.  Replace the "Model Selection" dropdown with a primary `st.selectbox` for **"Research Policy."**
    2.  Below the selector, display a summary of the chosen policy's goal (e.g., "Optimized for the highest quality analysis, may be slower and more expensive.").
    3.  Add an `st.expander` to show advanced users the detailed agent-to-model mapping for the selected policy.
    4.  Add a `st.selectbox` for **"Target Audience"** ("Executive," "Technical," "General") to control the `Writer`'s tone.

**3. Upgrade the Agent Orchestrator**

  * **File:** `src/agent/orchestrator.py`
  * **Action:**
    1.  Modify `run_research_pipeline` to accept a `policy_name`.
    2.  The orchestrator will load the corresponding policy from the config and pass the specific `model_id` to each agent's execution function.
    3.  Implement the new "Critic" step. After the `Writer` produces its first draft, the orchestrator will call the `Critic` agent. The `Critic`'s feedback will then be passed back to the `Writer` for a final revision before completing the run.

**4. Evolve Each Agent to its Phase 2 Capability**

  * **Planner -\> Dynamic Strategy Formulation:**

      * **File:** `src/agent/planner.py`
      * **Action:** Modify the Planner to output a structured **research plan** instead of just a list of queries. The plan should include `source_type_hint` (e.g., "academic", "news") for each query.

  * **Searcher -\> Source-Aware Query Routing:**

      * **Files:** `src/agent/searcher.py`, `src/providers/search_providers.py`
      * **Action:** Integrate a specialized search provider (e.g., a news API or academic search API). Modify the `Searcher` to read the `source_type_hint` from the Planner's output and route queries to the most appropriate provider.

  * **Reader -\> Structural Content Extraction:**

      * **Files:** `src/tools/fetch_url.py`, `src/storage/models.py`
      * **Action:**
        1.  Update the `Document` model in `models.py` to support structured content (e.g., a `content_blocks` list) instead of a single `text` string.
        2.  Enhance the `Reader` with libraries like `BeautifulSoup` to parse and store HTML structure (headings, tables, lists) in the new `content_blocks` field.

  * **Analyst -\> Context-Aware Claim Weighting:**

      * **File:** `src/agent/analyst.py`
      * **Action:** Upgrade the Analyst's prompt to leverage the new structured content from the `Reader`. It must now adjust its claim confidence based on the structural context (e.g., a claim in a table is more credible than a claim in a comment).

  * **Writer -\> Multi-Modal Report Generation:**

      * **File:** `src/agent/writer.py`
      * **Action:** Update the Writer's prompt to use the structured data from the Analyst (e.g., parsed tables, contradictions). It must now be capable of generating Markdown tables and other rich formatting in its output, tailored to the selected "Target Audience."

  * **Critic -\> New Agent for Quality Assurance:**

      * **File:** `src/agent/critic.py` (New File)
      * **Action:** Create the new `Critic` agent. Its function will take the draft report, the initial research plan, and the analyst's findings. Its prompt will be to critique the draft for completeness, accuracy, and adherence to the plan, producing actionable feedback for the `Writer`.

-----

#### **Part 3: Documentation Mandate**

You must update all relevant planning documents to reflect this significant architectural evolution.

1.  **`master-plan.md` & `prd.md`:** Restructure the roadmap. Replace the old Stage 2, 3, and 4 with a new "Phase 2 Agent Intelligence" stage that details these advanced capabilities.
2.  **All Spec Docs:** Update `docs/specs/*.md` to reflect the new agent behaviors, data models (especially for the `Document` and `Planner` outputs), and orchestration flow.
3.  **`README.md`:** Update the architecture diagram and features list to proudly showcase the new heterogeneous, multi-agent system and the policy-based user controls.

-----

#### **Part 4: Final Output**

Your final output must be a comprehensive package for project execution:

1.  **Updated Documentation:** The complete, revised text for all specified documentation files.
2.  **Coding Agent Workflow:** A detailed, step-by-step implementation plan organized by feature. For each step, specify the file to be modified, the functions to be changed, and the precise logic to be implemented.