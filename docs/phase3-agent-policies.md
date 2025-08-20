# Phase 3 — Dual Model Routing (Manual + Agent Policies)

Objective
- Enable both:
  - Manual single-model runs (user explicitly picks one provider/model)
  - Policy-based heterogeneous routing (each agent auto-picks an optimal model based on research mode and audience)
- Keep configuration simple and env-driven so it remains easy to operate in CI and local dev.

Current State (what the code does today)
- The UI exposes a single “Model Selection” and sets one model for the entire run:
  - Sets per-session model: [src/ui/main_panel.py](src/ui/main_panel.py:353)
  - Passes selected_model into the pipeline: [src/ui/main_panel.py](src/ui/main_panel.py:433)
  - Orchestrator stores it once and does not route per agent: [src/agent/orchestrator.py](src/agent/orchestrator.py:48)
  - Writer calls the LLM via OpenRouter without per-agent routing: [src/agent/writer.py](src/agent/writer.py:304)
- Agent policies exist in configuration but are not yet wired through the orchestrator/agents:
  - Policy config: [src/config.py](src/config.py:208)
  - Model resolvers: [src/config.py](src/config.py:523), [src/config.py](src/config.py:587)
- Critic references policies but does not actually invoke a model yet (stubbed output): [src/agent/critic.py](src/agent/critic.py:158)

Target Behavior
- Routing Modes:
  - manual: always use the single UI-selected model for all LLM calls
  - policy: dynamically route model per agent using AGENT_POLICIES and research mode preference (speed/balanced/quality) plus audience overrides for Writer (and later Critic)
  - hybrid: default to the UI-selected model for most agents, but allow policy routing for specific agents where it helps most (e.g., writer, critic)

Environment-Driven Configuration (simple and explicit)
- Add the following variables to .env (document in README and .env.example):
  - ROUTING_MODE=manual | policy | hybrid
  - RESEARCH_MODE="🚀 Quick Brief" | "⚖️ Balanced Analysis" | "🔬 Deep Dive"  (already supported)
  - SELECTED_MODEL=gpt-oss-120b-openrouter-default  (existing manual model fallback)
  - POLICY_ENABLED=true | false  (feature flag, optional; if set, overrides ROUTING_MODE=policy)
  - POLICY_AGENT_MODELS_[AGENT]=comma-separated list of models in preference order for the “balanced” tier (optional)
    - Example:
      - POLICY_AGENT_MODELS_PLANNER=gpt-oss-120b-openrouter-default,gemini-2.5-flash-openrouter-default,claude-sonnet-4-openrouter-default
      - POLICY_AGENT_MODELS_ANALYST=claude-sonnet-4-openrouter-default,gemini-2.5-pro-openrouter-default
      - POLICY_AGENT_MODELS_WRITER=claude-sonnet-4-openrouter-default,gemini-2.5-pro-openrouter-default
    - Rationale: keep env overrides simple. One list per agent in “balanced” mode. We will still use the built-in defaults in AGENT_POLICIES for “speed” and “quality” unless overrides are provided:
      - Optional advanced overrides (only if needed):
        - POLICY_AGENT_MODELS_[AGENT]_SPEED=…
        - POLICY_AGENT_MODELS_[AGENT]_QUALITY=…
- Provider keys (unchanged, already supported):
  - OPENROUTER_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY

High-Level Wiring Plan

1) Config enhancements (env parsing and routing decisions)
- Extend Config to read ROUTING_MODE and POLICY_AGENT_MODELS_* env vars at startup (or lazily on first access).
- Merge env-provided lists on top of built-in AGENT_POLICIES:
  - If POLICY_AGENT_MODELS_[AGENT] is set, use its order for the “balanced” preference for that agent.
  - If POLICY_AGENT_MODELS_[AGENT]_SPEED or _QUALITY is set, use them for those preferences.
- Add a small helper that resolves the active mode:
  - effective_routing_mode():
    - if POLICY_ENABLED=true → “policy”
    - else if ROUTING_MODE set → its value
    - else → “manual”
- No change to existing model validation functions; they will continue to ensure chosen models have the correct API keys available.

2) UI changes (minimal)
- Sidebar: add a small Routing selector (Manual / Policy / Hybrid) with a short help tooltip:
  - If Manual: keep current “Model Selection” section as-is.
  - If Policy or Hybrid: still show “Model Selection” but mark it as “fallback” (used in hybrid mode and as ultimate fallback).
- Optional: add a compact readout showing the resolved models per agent for transparency:
  - After selecting research mode and audience, compute and display:
    - Planner → model-X
    - Reader → model-Y
    - Analyst → model-Z
    - Verifier → model-A
    - Writer (audience) → model-B
    - Critic (audience) → model-C
  - This leverages existing resolvers without executing the pipeline.

3) Orchestrator: route models per stage
- On pipeline start:
  - Compute constraints by research mode: [src/config.py](src/config.py:498) and capture _model_preference
  - Determine routing_mode via Config (see step 1)
- For each stage:
  - manual:
    - use the single selected_model already passed through UI: [src/ui/main_panel.py](src/ui/main_panel.py:433) → [src/agent/orchestrator.py](src/agent/orchestrator.py:48)
  - policy:
    - resolve agent model via Config.get_agent_model(agent, preference, optional audience)
    - pass that model_key to the agent
  - hybrid:
    - default to the UI’s selected_model
    - override specific agents (initially Writer and Critic) by policy-resolved models
- No change to the searcher (no LLM needed)

4) Agents: accept model_key and pass it to providers
- Update agent function signatures and calls (backward compatible):
  - planner.plan(topic, constraints, model_key=None)
  - analyst.analyze(documents, chunks, sub_questions, topic, model_key=None)
  - verifier.verify(claims, citations, documents, constraints, model_key=None)
  - writer.write(..., target_audience, model_key=None)  → Provider called with this model_key when provided
  - critic.critique_report(..., target_audience, ..., model_key=None)  → to be used once Critic calls an actual model
- In each agent, when model_key is None fallback to the session’s single model (manual mode) to preserve current behavior.

5) Provider layer: allow explicit model_key on chat calls
- Add model_key parameter to the chat() function in OpenRouter client so an agent can explicitly override the session default:
  - When model_key is provided, construct the client with that model (or select model config via Config.get_available_models_dict()) before executing the call.
  - When omitted, preserve current behavior (use Config.get_current_model_config()).

6) Testing
- Extend tools/scripts/test_agent_policies.py to include a routing smoke test:
  - Set ROUTING_MODE=policy and a RESEARCH_MODE preference; verify Config.get_agent_model returns valid models for each agent and that validate_agent_policies() passes.
- Add a small unit test for hybrid logic (e.g., Writer uses policy, Planner uses manual).
- Keep UI tests unchanged except add checks for the new Routing selector visibility and the per-agent preview expander (if enabled).

7) Progressive rollout strategy
- Phase A (low risk):
  - Implement provider chat(model_key=...) override and thread it through Writer only.
  - Enable hybrid routing (only Writer policy-based) as an experimental option.
- Phase B:
  - Add Critic
- Phase C:
  - Add Planner, Analyst, Verifier with routing hooks
- At each phase, the “manual” mode remains available as a safety fallback.

Operational Guidance

- Quick start (manual):
  - ROUTING_MODE=manual
  - SELECTED_MODEL=gpt-oss-120b-openrouter-default
  - RESEARCH_MODE="⚖️ Balanced Analysis"
  - Run the app and choose the model in the UI.

- Policy-based routing:
  - ROUTING_MODE=policy
  - RESEARCH_MODE controls preference tier (speed/balanced/quality)
  - Optionally provide env overrides, e.g.:
    - POLICY_AGENT_MODELS_PLANNER=gpt-oss-120b-openrouter-default,gemini-2.5-flash-openrouter-default
    - POLICY_AGENT_MODELS_ANALYST=claude-sonnet-4-openrouter-default,gemini-2.5-pro-openrouter-default
  - Start research; the UI can display the resolved per-agent models for transparency.

- Hybrid:
  - ROUTING_MODE=hybrid
  - Keep SELECTED_MODEL set via UI for overall fallback
  - Initially, route Writer (and later Critic) via policy; expand to more agents as confidence grows.

Developer Notes (references)
- Policy base configuration and resolvers:
  - AGENT_POLICIES: [src/config.py](src/config.py:208)
  - get_agent_model(...): [src/config.py](src/config.py:523)
  - get_agent_parameters(...): [src/config.py](src/config.py:587)
  - apply_research_mode(...): [src/config.py](src/config.py:498)
- Current single-model flow wiring:
  - UI model selection: [src/ui/sidebar.py](src/ui/sidebar.py:223)
  - Per-session model set: [src/ui/main_panel.py](src/ui/main_panel.py:353)
  - Pipeline selected_model argument: [src/ui/main_panel.py](src/ui/main_panel.py:433)
  - Orchestrator state injection: [src/agent/orchestrator.py](src/agent/orchestrator.py:48)
  - Writer calls LLM: [src/agent/writer.py](src/agent/writer.py:304)
  - Critic policy use (placeholder): [src/agent/critic.py](src/agent/critic.py:158)

Deliverables Checklist
- Add env parsing and routing mode helpers in Config
- Introduce Routing selector in sidebar
- Orchestrator calls policy resolvers per stage when routing_mode=policy|hybrid
- Update agent signatures to accept model_key and thread to provider chat
- Add model_key override support in provider chat
- Tests for policy, hybrid, and manual routing
- README + .env.example updates for new variables

Roll-back plan
- Set ROUTING_MODE=manual to force legacy single-model behavior
- Leave all new code paths gated so they are no-ops in manual mode
