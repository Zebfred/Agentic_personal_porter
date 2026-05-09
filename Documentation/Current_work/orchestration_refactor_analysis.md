# Orchestration Refactor Analysis: CrewAI → LangGraph vs. Google ADK

> **Date:** 2026-05-08  
> **Scope:** Evaluate refactoring the Agentic Personal Porter's agent orchestration layer  
> **Current State:** Hybrid — CrewAI (`crew_manager.py`) + LangGraph (`first_serving_porter.py`)

---

## 1. Current Architecture Snapshot

Your orchestration is already a **hybrid** of two frameworks:

| Component | Framework | Role |
|:---|:---|:---|
| [crew_manager.py](file:///home/bizon/Programming/Agentic_workflows/Agentic_personal_porter/src/agents/crew_manager.py) | **CrewAI** (`Agent`, `Task`, `Crew`) | Sequential categorization pipeline (GTKY Librarian → Categorizer) |
| [first_serving_porter.py](file:///home/bizon/Programming/Agentic_workflows/Agentic_personal_porter/src/agents/first_serving_porter.py) | **LangGraph** (`create_react_agent`) | Chief-of-Staff agent with tool-calling (7 tools, ReAct loop) |
| [gtky_base_classifier.py](file:///home/bizon/Programming/Agentic_workflows/Agentic_personal_porter/src/agents/gtky_base_classifier.py) | **LangChain** (prompt + chain) | Batch LLM classification with fallback |
| [socratic_mirror_logic.py](file:///home/bizon/Programming/Agentic_workflows/Agentic_personal_porter/src/agents/socratic_mirror_logic.py) | **Pure Python** | Delta calculation engine (Intent vs. Actual) |
| [audit_inspector.py](file:///home/bizon/Programming/Agentic_workflows/Agentic_personal_porter/src/agents/audit_inspector.py) | **Pure Python** | Human-in-the-loop verification batching |

### Key Observations

1. **CrewAI is only used in one place** — `crew_manager.py` for a straightforward 1-2 task sequential crew.
2. **LangGraph is already the primary orchestrator** for the most complex agent (`first_serving_porter`).
3. The "heavy" agents (classifier, audit inspector, socratic mirror) are **framework-agnostic** pure Python/LangChain classes.
4. You already depend on `langchain-core`, `langgraph`, AND `crewai` — three overlapping dependency trees.

---

## 2. Option A: Full Migration to LangGraph

*Drop CrewAI entirely. Consolidate everything under the LangGraph + LangChain ecosystem.*

### Pros

| Benefit | Details |
|:---|:---|
| **You're already 70% there** | `first_serving_porter.py` is already LangGraph. The only CrewAI code is `crew_manager.py` (170 lines). Migration surface is small. |
| **Massive dependency cleanup** | Removing `crewai==1.14.4` and `crewai-tools==1.14.4` eliminates a heavy transitive tree (Pydantic conflicts, telemetry overlaps, its own embedded LangChain fork). |
| **Fine-grained control over token flow** | LangGraph's graph-based execution lets you insert explicit nodes for your `TokenCircuitBreakerHandler` rather than relying on callback hacks. |
| **Native checkpointing** | Pause/resume long-running categorization jobs. Critical for your batch classification pipeline that sleeps 2.5s between chunks. |
| **Human-in-the-loop as a first-class concept** | Your Audit Inspector's "Pending Verification" pattern maps directly to LangGraph's `interrupt_before`/`interrupt_after` primitives. |
| **Unified observability** | Single LangSmith trace across all agents instead of fragmented CrewAI + LangChain traces. |
| **Ecosystem alignment** | You already use `langchain-groq`, `langchain-openai`, `langchain-mongodb`, `langchain-core`. Staying in-family. |
| **Mature & battle-tested** | LangGraph has 2+ years of production hardening and the largest community of the three options. |

### Cons

| Risk | Details |
|:---|:---|
| **Boilerplate increase** | The CrewAI crew in `crew_manager.py` is ~60 lines of declarative role/task config. Replacing it with an explicit `StateGraph` will be ~100-150 lines of graph definition, state schema, and node functions. |
| **Graph mental model** | Debugging a `StateGraph` with conditional edges requires understanding the execution trace. More complex than CrewAI's "kickoff and pray." |
| **No built-in "role" abstraction** | CrewAI's `role`, `goal`, `backstory` pattern is ergonomic for defining agent personas. In LangGraph, you bake this into system prompts manually (which you already do for the Porter). |
| **LangChain ecosystem churn** | LangChain's deprecation velocity is high. You've already experienced this (migrating from `AgentExecutor` to `create_react_agent`). |

### Migration Effort: **Low** (1-2 days)

The `crew_manager.py` Crew is a simple sequential pipeline. It translates to:
```
[Categorizer Node] → [Conditional: isValuableDetour?] → [Curator Node] → [Save Results]
```

---

## 3. Option B: Full Migration to Google ADK

*Drop both CrewAI and LangGraph. Rebuild on the Google Agent Development Kit.*

### Pros

| Benefit | Details |
|:---|:---|
| **GCP-native deployment** | You're already targeting GCP (Cloud Run, Vertex AI). ADK has first-class `Vertex AI Agent Engine` and Cloud Run integrations. |
| **Built-in evaluation** | ADK ships with trajectory evaluation tools. You currently have no automated way to test agent behavior beyond health heartbeats. |
| **Developer UI** | ADK's built-in inspector lets you step through agent execution, inspect state changes, and replay decisions. Replaces your manual `[TRANSPARENCY HANDOFF]` log parsing. |
| **Multi-agent native** | ADK's agent composition model (parent/child agent delegation) maps cleanly to your Porter → Sub-agent architecture. |
| **Software engineering principles** | Modular, unit-testable agent definitions. Your current agents are already structured this way — ADK formalizes it. |
| **Model agnostic** | Despite being a Google product, ADK works with any LLM provider (Groq, OpenAI, etc.). Your multi-model strategy survives. |
| **OpenTelemetry native** | You already have `opentelemetry-api==1.34.1` in your deps. ADK instruments agents automatically. |

### Cons

| Risk | Details |
|:---|:---|
| **Full rewrite required** | Unlike LangGraph (where you're 70% migrated), moving to ADK means rewriting **all** agent orchestration from scratch. Every agent, every tool, every state flow. |
| **Lose LangChain ecosystem** | Your `langchain-groq`, `langchain-openai`, `langchain-mongodb` integrations would need to be replaced with ADK-native equivalents or raw SDK calls. This is a significant regression. |
| **Younger ecosystem** | ADK is ~1 year old vs LangGraph's 2+ years. Smaller community, fewer battle-tested patterns, sparser Stack Overflow coverage. |
| **Vendor gravity** | While technically model-agnostic, the ergonomic path pulls you toward Gemini models and Vertex AI. Given you're on Groq/Llama primarily, you'd be swimming upstream. |
| **Testing maturity** | ADK's evaluation tools are powerful but opinionated — they're designed around Google's agent patterns, not necessarily your "Sovereign Socratic" architecture. |
| **Dependency replacement scope** | You'd need to replace or wrap 4 LangChain integrations: `langchain-groq`, `langchain-openai`, `langchain-mongodb`, and potentially `langchain-core` (prompts, tools, messages). |

> [!WARNING]
> **Migration Effort: High (2-4 weeks)**  
> This is not a refactor — it's a replatform. Every agent file, every tool definition, every orchestration pattern, and your entire test suite would need to be rewritten.

---

## 4. Summary Decision Matrix

| Criteria | Stay Hybrid (Current) | Full LangGraph | Google ADK |
|:---|:---:|:---:|:---:|
| **Migration effort** | None | 🟢 Low (1-2 days) | 🔴 High (2-4 weeks) |
| **Dependency hygiene** | 🔴 3 overlapping trees | 🟢 Single ecosystem | 🟡 New ecosystem |
| **Control over execution** | 🟡 Mixed | 🟢 Maximum | 🟢 High |
| **Human-in-the-loop** | 🟡 Manual (Audit Inspector) | 🟢 Native primitives | 🟢 Native primitives |
| **GCP deployment story** | 🟡 Generic Docker | 🟡 Generic Docker | 🟢 First-class |
| **Observability** | 🔴 Fragmented | 🟢 LangSmith unified | 🟢 OTel native |
| **Existing code reuse** | 🟢 100% | 🟢 ~85% (only crew_manager rewrites) | 🔴 ~30% (pure Python logic survives) |
| **Community / support** | 🟡 | 🟢 Largest | 🟡 Growing |
| **Learning curve** | None | 🟡 Graph concepts | 🟡 New paradigms |
| **Future GCP features** | — | — | 🟢 First adopter |

---

## 5. Resolved Decisions

The following answers were provided on 2026-05-08 and lock in the strategic direction:

| Question | Answer | Impact |
|:---|:---|:---|
| **Primary LLM direction?** | Llama for general "management" agents. **Gemini Flash** for categorization/fast tasks on Google data (Calendar, Docs). Moving to **Vertex AI Model Garden**. | ADK is the long-term destination. Model-agnostic "plug and play" architecture is a hard requirement. |
| **Developer UI priority?** | **High.** ADK inspector is critical for understanding system behavior and demonstrating the system to others. | ADK's inspector is a differentiator that must be captured — either natively or via the eval-only hybrid. |
| **Deployment target?** | **Vertex AI Agent Engine** confirmed. | ADK's zero-config deployment path becomes a significant future advantage. |
| **Protobuf/OTel cleanup?** | Dropping older `opentelemetry-exporter-otlp-proto-http` enables moving to `protobuf>=6`. | Phase 1 dependency cleanup should target this explicitly. |

---

## 6. Approved Phased Roadmap

> [!IMPORTANT]
> **Strategy: LangGraph Now → ADK Eval → ADK Full (when ready)**
>
> This is a staged convergence toward ADK as the ultimate target, using LangGraph as the stable bridge.

### Phase 1: CrewAI → LangGraph Consolidation
**Effort:** 1-2 days | **Risk:** Low

| Task | Details |
|:---|:---|
| Rewrite `crew_manager.py` | Replace the CrewAI `Agent`/`Task`/`Crew` with a LangGraph `StateGraph`. The pipeline becomes: `[Categorizer Node] → [Conditional: isValuableDetour?] → [Curator Node] → [Save Results]` |
| Remove CrewAI deps | Drop `crewai==1.14.4` and `crewai-tools==1.14.4` from `pyproject.toml`. |
| Dependency cleanup | Audit transitive deps freed by CrewAI removal. Target `protobuf>=6` upgrade and drop the pinned `opentelemetry-exporter-otlp-proto-http`. |
| Validate | Run existing test suite. Verify `run_crew()` produces identical output via the new graph. |

**Deliverable:** Single-framework orchestration (LangGraph + LangChain), cleaner dependency tree, protobuf modernized.

---

### Phase 2: ADK Evaluation Integration
**Effort:** 3-5 days | **Risk:** Medium

| Task | Details |
|:---|:---|
| Install ADK eval tooling | Add `google-adk` (eval components only) to the project. |
| Define trajectory test cases | Write evaluation specs for the First-Serving Porter's tool-calling behavior (does it route correctly? does it call the right sub-agents?). |
| Baseline current agents | Run evals against existing LangGraph agents to establish performance baselines per model (Llama 3.3 70B, Gemini Flash). |
| Model comparison harness | Build a "plug and play" eval harness that can swap LLMs (Groq/Llama, Gemini Flash, OpenAI) and compare categorization accuracy, latency, and token cost. |
| ADK Inspector exploration | Experiment with ADK's developer UI to inspect agent execution traces. Determine if it can consume LangGraph execution data or if it requires ADK-native agents. |

**Deliverable:** Quantitative baselines for model selection, eval regression suite, informed decision on ADK inspector compatibility.

> [!NOTE]
> **This phase answers a critical question:** Can ADK's eval and inspector tools work *alongside* LangGraph, or do they require full ADK agents? This determines whether Phase 3 is necessary or if the hybrid is sufficient.

---

### Phase 3: Selective ADK Migration (Conditional)
**Effort:** 2-4 weeks | **Risk:** High | **Trigger:** Phase 2 proves ADK inspector requires native agents

| Task | Details |
|:---|:---|
| Model-agnostic agent abstraction | Design a thin agent interface that supports both LangGraph and ADK backends — the "plug and play" requirement. |
| Migrate categorization agents first | GTKY classifiers are the best candidates: they're stateless, batch-oriented, and will benefit most from Gemini Flash on Google data. |
| Porter migration last | The First-Serving Porter is the most complex agent (7 tools, ReAct loop, transparency logging). Migrate only after categorizers are stable on ADK. |
| Vertex AI Agent Engine deployment | Deploy the ADK-native agents to Vertex AI Agent Engine. Keep LangGraph agents on Cloud Run as fallback during transition. |

**Deliverable:** Full ADK orchestration deployed on Vertex AI Agent Engine with model-agnostic swappability.

---

## 7. Architecture Principle: Plug-and-Play Models

Your stated goal of finding "the best model for a given task" demands a deliberate abstraction. Regardless of framework, every agent should consume its LLM through an interface like:

```python
# Pseudocode — the contract, not the implementation
class AgentLLMConfig:
    """Decouples agent logic from model provider."""
    provider: Literal["groq", "vertex", "openai"]
    model: str                    # e.g. "llama-3.3-70b-versatile", "gemini-2.0-flash"
    temperature: float = 0.0
    max_tokens: int = 4096
    
    def get_chat_model(self) -> BaseChatModel:
        """Returns the appropriate LangChain/ADK chat model."""
        ...
```

This should be implemented in **Phase 1** so that Phase 2's eval harness can trivially swap models per agent. It also future-proofs Phase 3 — whether the orchestration is LangGraph or ADK, the model selection layer stays the same.

---

## 8. Dependency Cleanup Targets (Phase 1)

| Action | Current | Target |
|:---|:---|:---|
| **Remove** | `crewai==1.14.4` | — |
| **Remove** | `crewai-tools==1.14.4` | — |
| **Upgrade** | `protobuf>=5.0.0,<6.0.0` | `protobuf>=6.0.0,<7.0.0` |
| **Upgrade** | `opentelemetry-api==1.34.1` | Latest compatible with `protobuf>=6` |
| **Audit** | Transitive deps from CrewAI | Verify no orphaned packages remain |
