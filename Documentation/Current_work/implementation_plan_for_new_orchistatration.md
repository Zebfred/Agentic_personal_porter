# Phase 1: CrewAI → LangGraph Consolidation

> **Source of Truth:** [orchestration_refactor_analysis.md](file:///home/bizon/Programming/Agentic_workflows/Agentic_personal_porter/Documentation/Current_work/orchestration_refactor_analysis.md)  
> **Scope:** Phase 1 only — replace `crew_manager.py` with a LangGraph `StateGraph`, clean up deps.

---

## Context

The analysis document confirms:
- CrewAI is **only used in one file** — `crew_manager.py` (170 lines, sequential 1-2 task crew).
- LangGraph is **already the primary orchestrator** (`first_serving_porter.py`).
- All other agents (classifier, audit inspector, socratic mirror) are **framework-agnostic** pure Python/LangChain.
- Migration effort: **Low (1-2 days)**.

The existing `run_crew()` function does this:
1. Loads context and recent actuals from MongoDB.
2. Runs a **Categorizer** agent that maps the journal entry to one of 9 Hero Pillars.
3. Optionally runs a **Curator** agent if `isValuableDetour` is flagged.
4. Saves results to file + MongoDB.

This translates directly to a `StateGraph`:
```
[categorizer_node] → [conditional: isValuableDetour?] → [curator_node] → [save_results_node] → END
                                                    └─────────────────→ [save_results_node] → END
```

---

## Proposed Changes

---

### Dependencies

#### [MODIFY] [pyproject.toml](file:///home/bizon/Programming/Agentic_workflows/Agentic_personal_porter/pyproject.toml)
- **Remove** `crewai==1.14.4` (line 12)
- **Remove** `crewai-tools==1.14.4` (line 13)
- **Upgrade** `protobuf>=5.0.0,<6.0.0` → `protobuf>=6.0.0,<7.0.0` (line 41)
- **Audit** `opentelemetry-api==1.34.1` for compatibility with protobuf 6+ (update pin if needed)

> [!IMPORTANT]
> After editing `pyproject.toml`, we'll run `uv lock --upgrade` to regenerate `uv.lock` and verify that the dependency tree resolves cleanly without CrewAI's transitive conflicts.

---

### Agent Orchestration

#### [NEW] [porter_manager.py](file:///home/bizon/Programming/Agentic_workflows/Agentic_personal_porter/src/agents/porter_manager.py)

New LangGraph StateGraph that replaces the CrewAI Crew. Key design:

- **`ReflectionState` (TypedDict):** Holds `journal_entry`, `log_data`, `username`, `actuals_str`, `recon_result`, `curator_result`, `final_output`.
- **`categorizer_node`:** Uses `ChatGroq` (`llama-3.1-8b-instant`) with the existing Categorizer system prompt. Classifies the journal entry into one of the 9 Hero Pillars. Returns structured JSON: `{Pillar, Reason, Confidence_Score}`.
- **`curator_node`:** Uses `ChatGroq` (`llama-3.1-8b-instant`) with the existing GTKY Librarian prompt. Evaluates "Valuable Detour" entries against the Origin Story.
- **`save_results_node`:** Writes the reflection markdown to `data/reflections/daily_recon_{date}.md` and saves to MongoDB via `SovereignMongoStorage.save_agent_reflection()`.
- **`should_curate` (conditional edge):** Routes to `curator_node` if `log_data.get('isValuableDetour')` is truthy, otherwise skips directly to `save_results_node`.
- **`run_porter_reflection()`:** Public entry point that mirrors the old `run_crew()` signature: `(journal_entry: str, log_data: dict = None, username: str = "Hero") -> str`. This preserves the API contract so callers don't break.

The `TokenCircuitBreakerHandler` and `AgentHeartbeatManager` integration will be preserved identically.

#### [ARCHIVE] [crew_manager.py](file:///home/bizon/Programming/Agentic_workflows/Agentic_personal_porter/src/agents/crew_manager.py)
- Move to `.legacy_hr/crew_manager.py` per project rules.

---

### API Routing

#### [MODIFY] [journal_routes.py](file:///home/bizon/Programming/Agentic_workflows/Agentic_personal_porter/src/routes/journal_routes.py)

| Line | Change |
|:---|:---|
| 6 | Update docstring: "CrewAI" → "LangGraph" |
| 17 | `from src.agents.crew_manager import run_crew` → `from src.agents.porter_manager import run_porter_reflection` |
| 265 | `result_text = run_crew(enhanced_journal_entry, log_data)` → `result_text = run_porter_reflection(enhanced_journal_entry, log_data)` |
| 285 | Update error log message: "CrewAI" → "LangGraph" |

---

### Docstring / Comment Cleanup

#### [MODIFY] [socratic_mirror_logic.py](file:///home/bizon/Programming/Agentic_workflows/Agentic_personal_porter/src/agents/socratic_mirror_logic.py)
- Line 97: Update docstring from "Converts raw data into a Socratic Prompt for the CrewAI Agent" → "Converts raw data into a Socratic Prompt for the Categorizer Agent"

#### [MODIFY] [Dockerfile](file:///home/bizon/Programming/Agentic_workflows/Agentic_personal_porter/Dockerfile)
- Line 47: Update comment "CrewAI artifacts" → "Agent artifacts"

---

### Phase 1 Dependency Cleanup Summary

| Action | Current | Target |
|:---|:---|:---|
| **Remove** | `crewai==1.14.4` | — |
| **Remove** | `crewai-tools==1.14.4` | — |
| **Upgrade** | `protobuf>=5.0.0,<6.0.0` | `protobuf>=6.0.0,<7.0.0` |
| **Audit** | `opentelemetry-api==1.34.1` | Latest compatible with protobuf 6 |
| **Audit** | Transitive deps from CrewAI | Verify no orphaned packages |

---

## Out of Scope (Future Phases)

Per the analysis doc's phased roadmap:
- **Phase 2 (ADK Eval Integration):** Install ADK eval tooling, build model comparison harness, baseline agents — 3-5 days.
- **Phase 3 (Selective ADK Migration):** Conditional on Phase 2 findings — 2-4 weeks.
- **`AgentLLMConfig` abstraction:** The plug-and-play model interface from Section 7 of the analysis doc. Should be implemented in Phase 1 but is a separate task from the CrewAI removal.

> [!NOTE]
> The `AgentLLMConfig` pattern described in the analysis doc (Section 7) is a natural follow-up. Should I include it in this Phase 1 scope, or keep it as a separate task?

---

## Verification Plan

### Automated Tests
1. `uv lock --upgrade` — verify dependency resolution succeeds without crewai/protobuf conflicts.
2. `uv sync` — verify the venv installs cleanly.
3. `python -c "from src.agents.porter_manager import run_porter_reflection"` — verify the new module imports without errors.
4. Run existing test suite via `pytest` to check for regressions.

### Manual Verification
- Test the `/process_journal` route with a sample journal entry payload.
- Verify the LangGraph agent produces a valid `{Pillar, Reason, Confidence_Score}` JSON response.
- Verify `data/reflections/daily_recon_{date}.md` is generated correctly.
- Verify MongoDB `save_agent_reflection` is called with the correct shape.
