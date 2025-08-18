Excellent questions. Now that the UI is on a clear path to improvement, focusing on the core output—the quality of the research itself—is the perfect next step. This is where Nova Brief can truly differentiate itself.

Here is a breakdown of what more can be done to generate higher-quality reports, including how to handle user preferences and enhance the agent pipeline.

---

### The Strategy: Introduce "Research Modes"

Instead of asking the user to manually tweak a dozen settings, you can bundle them into simple, intent-driven presets. This directly addresses your question about "speed vs. quality" by making it an explicit choice for the user, simplifying the interface while offering powerful control.

**Implementation:**
In the Streamlit sidebar (`src/app.py`), replace some of the individual sliders with a single `st.radio` or `st.selectbox` for "Research Mode":

* **🚀 Quick Brief (Speed-focused):**
    * **Goal:** Get a rapid, high-level overview.
    * **Agent Tuning:**
        * `max_rounds`: 1
        * `per_domain_cap`: 2
        * Search Provider: Use only the fastest provider (e.g., DuckDuckGo).
        * Report Length: Prompt the `Writer` for a concise 400-600 word summary.
        * Model: Could be configured to use a faster, smaller model if available.

* **⚖️ Balanced Analysis (Default):**
    * **Goal:** A thorough report with a good balance of speed and depth.
    * **Agent Tuning:** This would use your current default settings.
        * `max_rounds`: 2-3
        * `per_domain_cap`: 3
        * Report Length: Target the standard 800-1,200 words.

* **🔬 Deep Dive (Quality-focused):**
    * **Goal:** A comprehensive, in-depth report that prioritizes completeness over speed.
    * **Agent Tuning:**
        * `max_rounds`: 4-5
        * `per_domain_cap`: 4-5
        * Search Provider: Use multiple providers simultaneously (see Agent Enhancements below).
        * Report Length: Prompt the `Writer` for a detailed 1,500-2,000 word analysis.

This "Research Mode" approach elegantly handles the report length question. The length becomes an *outcome* of the user's desired research depth, not an arbitrary setting they have to guess at.

---

### Agent Enhancements for Higher Usefulness & Quality

To power these modes and increase the quality of the output, we can make each agent in your pipeline smarter.

#### 1. Planner Agent: Make it Iterative & Reflective

Currently, the `Planner` runs once at the beginning. A truly intelligent agent would reflect on what it has learned and adjust its plan.

* **What to do:** After the first round of searching and analysis, re-invoke the `Planner` agent.
* **New Prompt for the Planner:** *"Based on the initial claims and sources found, what information is still missing? Are there any new avenues of inquiry that have emerged? Generate 3-4 new, highly-specific queries to fill these gaps."*
* **Implementation:** In `src/agent/orchestrator.py`, add a call to a new `planner.refine_plan()` function within the main research loop, specifically after the `Verifier` identifies that more information is needed.

#### 2. Searcher Agent: Use Multi-Provider & Specialized Search

Your current setup relies on a single search provider. Relying on one source limits the breadth and quality of your results.

* **What to do:** Augment the `Searcher` to query multiple sources simultaneously and select the best one for the job. Your PRD already mentions potentially using Tavily, Bing, or Brave.
* **Implementation:**
    1.  Integrate Tavily or another search provider API into `src/providers/search_providers.py`.
    2.  In the `searcher.search()` function, use `asyncio.gather` to run queries against **both** DuckDuckGo and the new provider(s) in parallel.
    3.  Merge and de-duplicate the results. The `Planner` could even be enhanced to tag certain queries as "best for academic search" or "best for news search," directing them to the appropriate provider.

#### 3. Analyst Agent: Add Contradiction Detection

A high-quality report doesn't just list facts; it synthesizes them. A key part of synthesis is identifying where sources agree, disagree, or offer different perspectives.

* **What to do:** Upgrade the `Analyst` from a simple claim extractor to a true synthesizer.
* **New Prompt for the Analyst:** After instructing it to extract claims, add: *"Now, review all extracted claims. Identify any claims that appear to contradict each other or offer conflicting data points. Also, group together claims that provide strong, multi-source support for the same key finding."*
* **Implementation:** Update the `ANALYSIS_SYSTEM_PROMPT` in `src/agent/analyst.py`. The JSON output schema can be modified to include new keys like `"contradictions": []` and `"supporting_clusters": []`. This structured data would be invaluable to the `Writer`.

#### 4. Writer Agent: Introduce Audience & Tone Customization

The definition of a "high-quality report" depends on who is reading it. An executive brief is very different from a technical deep-dive.

* **What to do:** Allow the user to specify the target audience for the report.
* **Implementation:**
    1.  In `src/app.py`, add an `st.selectbox` for "Target Audience" with options like "Executive Summary," "Technical Report," and "General Audience."
    2.  Pass this selection to the `writer.write()` function.
    3.  Modify the `WRITING_SYSTEM_PROMPT` in `src/agent/writer.py` to include the audience. For example: *"You are writing for a **Technical Expert**. Prioritize data, detailed explanations, and specific terminology. Write a comprehensive, in-depth analysis."*

---

### Prioritized Action Plan

1.  **Implement Research Modes:** Start by adding the "Research Mode" radio button in the UI. This provides immediate user value and a framework for the other changes.
2.  **Enhance the `Analyst` for Contradiction Detection:** This is a prompt and schema change that can significantly increase the depth of the generated report without major architectural changes.
3.  **Implement `Writer` Audience Customization:** Like the `Analyst` change, this is primarily a prompt engineering task that adds a powerful layer of customization to the final output.
4.  **Integrate a Second Search Provider:** This is a more involved step but is crucial for improving the diversity and quality of the source material.
5.  **Make the `Planner` Iterative:** This is the most complex change but has the potential to make the agent feel truly intelligent and adaptive.