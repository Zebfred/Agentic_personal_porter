# Model Garden vs Agent Garden vs ADK — Mach4 Comparison

> **Date**: 2026-05-11
> **Context**: Evaluating the fastest path to baseline usability for the Agentic Personal Porter.

## 1. The Three Axes

The Agentic Porter project sits at the intersection of three Google Cloud products. Each solves a different problem:

| Axis | What It Is | Our Question |
|---|---|---|
| **Model Garden** | Library of 200+ foundation models | "Which brain for which task?" |
| **Agent Garden** | Curated library of pre-built agent templates | "Is there a template we can fork?" |
| **ADK** | Code-first framework for building/evaluating agents | "How do we build our own with full control?" |

```
┌────────────────────────────────────────────────────────────┐
│                    Vertex AI Ecosystem                     │
│                                                            │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │
│  │ Model Garden │   │ Agent Garden │   │     ADK      │   │
│  │ ~200 models  │   │  Templates   │   │  Framework   │   │
│  │ ~50 for text │   │  Blueprints  │   │  Eval + UI   │   │
│  │              │   │  Samples     │   │  Inspector   │   │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘   │
│         │                  │                   │           │
│         └─────────────┬────┴───────────────────┘           │
│                       │                                    │
│               ┌───────▼────────┐                           │
│               │  Agent Engine  │                           │
│               │  (Managed      │                           │
│               │   Runtime)     │                           │
│               └────────────────┘                           │
└────────────────────────────────────────────────────────────┘
```

---

## 2. Model Garden Assessment

### Models We've Tested

| Provider | Model | Classification Accuracy | Tool-Call Accuracy | Avg Latency |
|---|---|---|---|---|
| `google_genai` | gemini-2.5-pro | **4/4 (100%)** | ⏳ Pending | ~2s |
| `google_genai` | gemini-2.5-flash | 3/4 (75%) | ⏳ Pending | ~1.5s |
| `groq` | llama-3.3-70b-versatile | N/A | **4/4 (100%)** | **0.29s** |
| `groq` | llama-3.1-8b-instant | N/A | 4/4 tools, 3/4 args | 0.39s |

### Key Findings

1. **Llama 3.3 70B on Groq**: Perfect tool-call accuracy at 0.29s latency — 7x faster than Gemini.
   This is a strong candidate for the orchestration/routing layer where speed matters.
2. **Gemini 2.5 Pro**: 100% on classification. Pending tool-call eval (credits depleted today).
   Best candidate for high-reasoning tasks like the Historian classifier.
3. **Llama 3.1 8B**: Good tool selection but weaker argument extraction (empty `query` field on search).
   Not suitable for production but could work as a local dev/test model.

### Recommendation: Hybrid Architecture

| Role | Recommended Model | Why |
|---|---|---|
| **Categorizer** (fast, batch) | `gemini-2.5-flash` | 75% accuracy, low cost, sufficient for tagging |
| **Historian** (deep reasoning) | `gemini-2.5-pro` | 100% accuracy, best for nuanced classification |
| **Orchestrator** (tool routing) | `llama-3.3-70b` OR `gemini-2.5-pro` | Both score 100%; Llama is 7x faster but Gemini has richer reasoning |
| **Manager nodes** (simple tasks) | `gemini-2.5-flash` | Already deployed, working well |

---

## 3. Agent Garden Assessment

### What's Available

Agent Garden provides pre-built templates deployed via the Google Cloud console. As of May 2026:

| Template Category | Relevance to Porter | Customization Needed |
|---|---|---|
| **Customer Service** | Low — wrong domain | High |
| **Data Analysis (BigQuery)** | Medium — similar pattern | Medium |
| **Research & Information** | Medium — closest to our vibe check | Medium |
| **Creative/Content** | Low | High |
| **Data Engineering** | Low | High |

### Fit Analysis for Porter

> **Verdict: No direct match.** Agent Garden excels at enterprise patterns (customer support, data pipelines) but has no personal productivity or self-quantification template.

However, the **architectural patterns** from Agent Garden are valuable:
- **RAG-based search agent**: Similar to our Weaviate/Chroma dual-search pattern
- **Multi-agent coordinator**: Similar to our Porter → sub-agent routing

### Can We Fork a Template?

The samples are built using ADK, so they serve as excellent **reference architectures**. The closest analogue would be a Research & Information template customized with our tools. But the customization cost is roughly equivalent to building from scratch with ADK.

### Is Agent Garden Model-Agnostic?

**Yes.** Samples are optimized for Gemini but the underlying ADK framework supports any model via Model Garden. You could swap Gemini for Llama in a template — the ADK `model` parameter is just a string.

---

## 4. ADK Assessment

### What ADK Gives Us vs What We Already Have

| Capability | Our Current Setup (LangGraph) | ADK Native |
|---|---|---|
| **Agent Definition** | `create_react_agent(llm, tools, prompt)` | `Agent(name, model, instruction, tools)` |
| **Tool Binding** | `@tool` decorator + `bind_tools()` | Plain functions (auto-wrapped) |
| **Orchestration** | LangGraph nodes + edges | `sub_agents`, `SequentialAgent`, `ParallelAgent` |
| **Eval: Tool Trajectory** | Custom harness (`orchestration_harness.py`) | `adk eval` + `.evalset.json` |
| **Eval: Response Quality** | Custom comparison (`model_comparison_harness.py`) | ROUGE-1 or LLM-as-judge |
| **Eval: User Simulation** | Not implemented | Built-in multi-turn generation |
| **Debug UI** | None (console only) | **ADK Inspector** — visual trace viewer |
| **State Management** | LangGraph state dict | ADK session + `output_key` state passing |
| **Model Swap** | `AgentLLMConfig` factory | `model="model_id"` parameter |
| **CI/CD Integration** | Not implemented | `adk eval` → pytest integration |
| **Deployment** | Manual (Docker/Cloud Run) | Agent Engine (managed) |

### The Inspector Question

> **Can ADK Inspector attach to LangGraph agents?**

**No.** Inspector is native to ADK's execution runtime. It requires agents built with `google.adk.agents.Agent`. However, ADK supports `LangchainAgent` as a wrapper — if we wrap our LangGraph agent in an ADK shell, Inspector could potentially trace it. This is an untested path.

### Migration Cost Estimate

| Component | Effort | Notes |
|---|---|---|
| Porter ReAct → ADK Agent | **Low** | Already prototyped in `porter_adk_prototype/` |
| Tool definitions | **Trivial** | Remove `@tool` decorators, use plain functions |
| System prompt | **Trivial** | Copy/paste `instruction` parameter |
| Sub-agent routing | **Medium** | Replace LangGraph edges with `sub_agents` |
| State management | **Medium** | Migrate from LangGraph state to ADK sessions |
| Eval harness | **Low** | Convert `trajectory_tests.py` → `.evalset.json` (done) |
| Frontend integration | **High** | ADK has its own session/memory model |

### ADK Prototype Status

Working prototype built in `scratch/Exploring_adk/porter_adk_prototype/`:
- `agent.py` — ADK Agent with all 7 tools + Porter system prompt
- `tools.py` — Mock tool implementations
- `run_porter.py` — CLI runner with `--smoke-test` mode
- `porter.evalset.json` — 8 test cases in ADK native format

**Blocked by**: Gemini API credit propagation (prepayment credits depleted today).

---

## 5. Recommendation for Mach4

### Architecture Strategy

```
Phase 1 (Now): Keep LangGraph for production, use ADK for eval
  ├── LangGraph Porter stays as-is (battle-tested)
  ├── Use ADK's evalset.json format for test cases
  ├── Run adk eval against ADK prototype for comparison
  └── Use ADK Inspector for debugging (via prototype)

Phase 2 (After baseline usability): Selective migration
  ├── Migrate stateless nodes to ADK (categorizer, curator)
  ├── Keep Porter ReAct loop in LangGraph (complex state)
  └── Use ADK eval CI/CD for regression testing

Phase 3 (Mach5): Full ADK migration
  ├── Porter → ADK Agent with sub_agents
  ├── Agent Engine deployment
  └── Inspector for production debugging
```

### Why Not Migrate Everything Now?

The meta goal is **baseline usability with mid-quality calendar data**. A full framework migration would delay that. The pragmatic path:

1. ✅ Use the **best model for each task** (hybrid Gemini + Llama)
2. ✅ Use ADK's **eval tooling** without migrating the agent itself
3. ⏳ Build usability features on the battle-tested LangGraph stack
4. 🔮 Migrate to ADK when the framework proves value via the prototype

---

## 6. Open Items

- [ ] Gemini tool-call eval results (once credits propagate)
- [ ] Gemini 3.1 Pro Preview eval (when available)
- [ ] Llama 4 Maverick MaaS access test
- [ ] ADK Inspector hands-on evaluation
- [ ] Agent Engine deployment cost estimate
