# Local Ollama Routing & Triage Blueprint (Handoff Specification)

> **Status:** Deferred for future Agentic Personal Porter sprint.
> **Hardware Target:** Ubuntu Desktop Host (NVIDIA GeForce RTX 4090, 24 GB VRAM) running local `ollama.service` (`http://localhost:11434`).
> **Pre-Pulled Base Models:** `bge-m3:latest` (1.2 GB) and `llama3.1:8b` (4.9 GB).

---

## 1. Architectural Objective

Integrate local Ollama inference into the Agentic Personal Porter ecosystem to achieve:
1. **Zero-Cost Local Embeddings (`bge-m3`):** Eliminate mock-vector fallbacks and external embedding API dependencies by routing [`BGEM3EmbeddingsClient`](../../src/integrations/embeddings_client.py) directly to local Ollama.
2. **Confidence-Gated SLM Triage (The 90/10 Rule):** Route routine calendar and journal categorizations through a local 7B–14B Ollama model first. Only escalate to cloud reasoning tiers (`Groq` / `Gemini`) when `Confidence_Score < 80` or when an event is flagged as a `Valuable Detour`.
3. **Sovereign Offline Fallback:** Allow [`get_resilient_llm`](../../src/utils/llm_resilience.py) to read the host's verified model hot-list (`verified_host_models.json`) and dynamically include local Ollama models in the resilience chain.

---

## 2. Target Files & Line-Numbered Implementation Guide

### A. Extend [`src/utils/llm_factory.py`](../../src/utils/llm_factory.py) (Lines 9–79)

* **Reasoning:** Currently, `AgentLLMConfig.provider` is restricted to `Literal["groq", "openai", "vertex", "google_genai"]`. Adding `"ollama"` via `ChatOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")` or `langchain_ollama.ChatOllama` allows any LangChain/LangGraph agent to instantiate local Ollama models with zero cloud token burn.
* **Proposed Edit (Lines 14–79):**
  ```python
  # Line 14: Add "ollama" to supported provider literals
  provider: Literal["groq", "openai", "vertex", "google_genai", "ollama"]
  ```
  ```python
  # Lines 78-89: Add ollama branch before final ValueError
          elif self.provider == "ollama":
              from langchain_openai import ChatOpenAI
              base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
              return ChatOpenAI(
                  base_url=base_url,
                  api_key=SecretStr("ollama"),
                  model=self.model,
                  temperature=self.temperature,
                  max_tokens=self.max_tokens,
                  **kwargs
              )
  ```

### B. Add Tier-0 / Fallback Profiles in [`src/utils/llm_resilience.py`](../../src/utils/llm_resilience.py) (Lines 24–100)

* **Reasoning:** Batch classification tasks (`gtky_classifier`, `categorizer`) frequently hit Groq 429 rate limits during historical backfills. Adding a local Ollama tier (`TIER_0_LOCAL_CONFIG`) prevents rate-limit stalls while preserving cloud failover if the local GPU is busy.
* **Proposed Edit (Lines 24–45):**
  ```python
  TIER_0_LOCAL_CONFIG = AgentLLMConfig(
      provider="ollama",
      model=os.getenv("OLLAMA_DEFAULT_MODEL", "llama3.1:8b"),
      temperature=0.0,
      max_tokens=4096,
  )
  ```

### C. Confidence-Gated SLM Triage in [`src/agents/porter_manager.py`](../../src/agents/porter_manager.py) (Lines 43–148)

* **Reasoning:** [`categorizer_node`](../../src/agents/porter_manager.py) currently invokes `groq/llama-3.3-70b-versatile` for every single event. By invoking `ollama_chat/llama3.1:8b` first and inspecting `CategorizationResult.Confidence_Score`, routine events (`Confidence_Score >= 80`) complete locally in `<250ms` while ambiguous events automatically re-run on Tier 1 cloud models.

### D. Verify Local Embeddings in [`src/integrations/embeddings_client.py`](../../src/integrations/embeddings_client.py) (Lines 11–30)

* **Reasoning:** Ollama's `/api/embeddings` (and `/api/embed` in newer Ollama versions) serves `bge-m3:latest` directly on `localhost:11434`.
* **Edge Case Note:** Ensure `self.model_name = os.getenv("BGE_M3_MODEL", "bge-m3:latest")` handles both `/api/embeddings` (`{"embedding": [...]}`) and `/api/embed` (`{"embeddings": [[...]]}`) response schemas.

---

## 3. Verification Checklist for Future Agent

- [ ] Run unit tests with mocked Ollama responses (`make verify-done`).
- [ ] Run [`src/agents/evals/model_comparison_harness.py`](../../src/agents/evals/model_comparison_harness.py) including `AgentLLMConfig(provider="ollama", model="llama3.1:8b")`.
- [ ] Update [`documentation/current-work/active-agent-dev.md`](../current-work/active-agent-dev.md) Verification Log upon completion.
