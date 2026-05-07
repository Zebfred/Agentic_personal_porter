# Dependency Stabilization & LangGraph Migration (May 2026)

## Overview
This document chronicles the dependency untangling, environment sanitation, and architectural refactoring performed to resolve massive dependency resolution loops ("resolution-too-deep") and successfully stabilize the Agentic Personal Porter's build and test environments.

## 1. The "Resolution-Too-Deep" Crisis
**The Issue:**
The core environment encountered catastrophic `pip` resolution failures (exceeding maximum depth) during Docker builds and local environment syncs. This was caused by conflicting version requirements between legacy machine learning frameworks (`tensorflow`, `tf-keras`), outdated data parsing libraries (`protobuf`), and modern agentic orchestration tools (`crewai`, `langchain`).

**The Remediation:**
- **Purged Dead Weight:** Removed `tensorflow`, `tf-keras`, `sklearn`, and `opentelemetry-proto` which were bloat-inducing and clashing with modern sub-dependencies.
- **Pinning Critical Constraints:** Imposed strict guardrails on `protobuf` (`>=5.0.0, <6.0.0`) and `urllib3` to prevent aggressive sub-dependency upgrades from breaking Kubernetes and Docker integrations.
- **ABI Check Modernization:** Updated the Dockerfile ABI integrity check to utilize `torch` and `onnxruntime` instead of `tensorflow`.

## 2. Ghost Metadata & Local Environment Corruption
**The Issue:**
During the aggressive purging and uninstallation of the clashing dependencies, the physical Python files for core transitive packages (`anyio`, `markupsafe`, `tokenizers`) were deleted, but their `.dist-info` metadata folders remained. This created "Ghost Packages" where `pip` falsely reported the packages as installed, but runtime execution (`pytest`) crashed with `ModuleNotFoundError`.

**The Remediation:**
- Executed strict `--force-reinstall` commands via `conda run` to force `pip` to ignore the corrupted metadata and fetch clean binaries from PyPI.
- Addressed downstream dependency drift (e.g., `crewai` requiring `click~=8.1.7` vs. PyPI fetching `click 8.3.3`) by firmly defining transitive pins in `requirements.txt` (`typer~=0.9.0`, `rich==14.3.4`) and running a final resolving `pip install -r requirements.txt`.

## 3. LangChain v1.x Architectural Migration
**The Issue:**
Forcing the environment upgrade to `langchain>=1.2.1` and `langgraph>=1.1.10` crossed a major breaking-change boundary. LangChain deprecated and entirely removed the legacy `AgentExecutor` and `create_tool_calling_agent` APIs from their core `langchain.agents` namespace, forcing all routing through LangGraph. This caused instant import crashes in `src/agents/first_serving_porter.py`.

**The Remediation:**
- **Ripped out Legacy Routing:** Completely removed `AgentExecutor` and legacy `PromptTemplate` imports.
- **Migrated to LangGraph:** Rewrote the agent instantiation to use `langgraph.prebuilt.create_react_agent`.
- **Dynamic State Modifiers:** Transitioned the static dictionary-based `invoke()` payloads to LangGraph's new state mechanic, passing system prompts via `state_modifier` and routing queries through `HumanMessage` structures.
- **Result:** Successfully bypassed the deprecation crash, achieving a 100% test pass rate (69/69 tests passed, 0 errors).

## Future Recommendations
- Do not blindly run `--force-reinstall` without tracking the downstream effects on strictly pinned sub-dependencies.
- The `sentence_transformers` package remains a heavy dependency for the currently inactive `chunking.py` legacy code. If local embeddings are abandoned in favor of API-based embeddings (e.g., OpenAI/Groq), this package should be entirely removed to vastly speed up Docker builds and reduce image bloat.
