Of course. Here is a comprehensive prompt that combines the concepts of the "LLM-as-Judge" and the "Critic" agent, and includes the request for a new, professionally formatted PDF evaluation report.

This prompt is designed to be a single, detailed directive for your Roo Code Agent to execute a major upgrade to the project's quality assurance and reporting capabilities.

-----

### **Master Prompt for Roo Code Agent: Implementing the Self-Correcting Generation & Advanced Evaluation Loop**

**Role:** You are the Lead Architect and Implementation Agent for the Nova Brief project.

**Objective:** Your mission is to implement a state-of-the-art, self-correcting generation and evaluation system. This involves two synergistic upgrades:

1.  **The "Critic" Agent:** An internal agent that reviews and refines the research report *before* it's finalized, dramatically improving its quality.
2.  **The "LLM-as-Judge":** An advanced evaluation mechanism in the harness that uses the same quality criteria as the Critic to produce a more thorough and credible evaluation report.

Finally, you will upgrade the evaluation harness to generate a professionally formatted **PDF report** summarizing these new, richer evaluation metrics, in addition to the existing JSON output.

-----

#### **Part 1: The Core Concept - A Unified Quality Rubric**

The foundation of this upgrade is a single, powerful **"Quality Rubric."** This rubric is a set of evaluation criteria that will be used by both the in-process **Critic** (to guide generation) and the post-process **Judge** (to score the final output). This creates a perfect feedback loop, ensuring our agent is optimized to excel at the very metrics it's judged on.

-----

#### **Part 2: Implementation Plan - The "Critic" Agent (In-Process Refinement)**

Your first task is to build and integrate the Critic agent to improve report quality during generation.

1.  **Create the Critic Agent Module:**

      * **File:** `src/agent/critic.py` (New File)
      * **Function:** Implement a primary function, `review(draft_report: str, state: ResearchState) -> Dict`.

2.  **Design the Critic's "Editorial Review" Prompt:**

      * This prompt instructs the LLM to act as an editor and provide actionable feedback.
      * **System Prompt:**
        ```
        You are a meticulous editor reviewing a draft AI-generated research report. Your goal is to identify specific flaws and provide actionable revisions. Respond ONLY with a valid JSON object in the format: {"is_publishable": boolean, "revisions_needed": ["Specific revision instruction 1.", "Specific revision instruction 2."]}
        ```
      * **User Prompt:**
        ```
        Please review this draft report against our quality rubric.

        1.  **Comprehensiveness:** Does the report fully address all initial sub-questions? (Sub-Questions: {list_of_sub_questions})
        2.  **Synthesis & Depth:** Does the report merely list facts, or does it synthesize them into a coherent narrative?

        **Draft Report:**
        ---
        {draft_report_content}
        ---

        Provide your evaluation. If it's not publishable, list the necessary revisions.
        ```

3.  **Integrate the Critic into the Orchestrator:**

      * **File:** `src/agent/orchestrator.py`
      * **Action:** Modify the main pipeline to include a two-stage writing process.
        1.  The `Writer` agent generates a first draft.
        2.  The `Orchestrator` calls `critic.review()` with the draft.
        3.  If `is_publishable` is `false`, the `Orchestrator` calls the `Writer` a **second time**, providing the original draft along with the `revisions_needed` from the Critic, instructing it to apply the feedback.

-----

#### **Part 3: Implementation Plan - The "LLM-as-Judge" (Advanced Evaluation)**

Next, you will upgrade the evaluation harness to use the same quality rubric for a more thorough final scoring.

1.  **Upgrade the Evaluation Harness:**

      * **File:** `eval/harness.py`
      * **Action:** Replace the current `_evaluate_content_coverage` function with a new, more comprehensive function: `_evaluate_semantic_quality`.

2.  **Design the Judge's "Scoring" Prompt:**

      * This prompt uses the same criteria as the Critic but asks for a quantitative score instead of qualitative feedback.
      * **System Prompt:**
        ```
        You are an impartial AI evaluator. Your task is to score a research report based on a quality rubric. Respond ONLY with a valid JSON object in the format: {"comprehensiveness_score": float, "synthesis_score": float, "clarity_score": float, "overall_quality_score": float, "justification": "A brief summary of your scoring."}
        ```
      * **User Prompt:**
        ```
        Please score the following report from 0.0 to 1.0 on each rubric item.

        **Rubric:**
        1.  **Comprehensiveness:** Does the report fully address all initial sub-questions? (Sub-Questions: {list_of_sub_questions})
        2.  **Synthesis & Depth:** Does the report synthesize information or just list facts?
        3.  **Clarity & Coherence:** Is the report well-structured and easy to understand?

        **Report to Score:**
        ---
        {final_report_content}
        ---

        Provide your scores now.
        ```

-----

#### **Part 4: Implementation Plan - The PDF Evaluation Report**

Finally, you will create a new output format for the evaluation harness to make the results professional and shareable.

1.  **Add a PDF Generation Library:**

      * **File:** `pyproject.toml`
      * **Action:** Add a new dependency for generating PDFs, such as `fpdf2`.

2.  **Create a Report Generator Module:**

      * **File:** `eval/report_generator.py` (New File)
      * **Function:** Implement a function, `create_pdf_report(eval_results: Dict, output_filename: str)`. This function will take the final JSON output from the harness as input.

3.  **Design the PDF Report Structure:**

      * The generated PDF should be a clean, professional document containing:
          * A **Title Page** ("Nova Brief Evaluation Report" with a timestamp).
          * An **Executive Summary** with top-line metrics (e.g., Overall Success Rate, Best Performing Model).
          * A **Comparison Table** showing each model tested, with columns for Speed, Cost (if available), and the new "Overall Quality Score."
          * A **Detailed Score Breakdown** section with tables showing the average scores for `comprehensiveness`, `synthesis`, and `clarity` for each model.

4.  **Integrate PDF Generation into the Harness:**

      * **File:** `eval/harness.py`
      * **Action:** At the end of the main evaluation function, after the results JSON has been saved, add a call to `report_generator.create_pdf_report()` to generate the corresponding PDF document.

-----

#### **Part 5: Final Output**

Your final output must be a complete implementation plan, including:

1.  **Updated Documentation:** The revised text for all relevant planning documents (`master-plan.md`, `prd.md`, specs, etc.) to reflect these new "Critic" and "Advanced Evaluation" capabilities.
2.  **Coding Agent Workflow:** A step-by-step guide detailing the creation of the new `critic.py` and `report_generator.py` files, the necessary modifications to `orchestrator.py` and `harness.py`, and the exact prompt designs to be implemented.