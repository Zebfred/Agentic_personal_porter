# Year 0: Chronicle of the Agentic Personal Porter

> A retrospective chronicling the foundational evolution of the **Agentic Personal Porter** ecosystem—from its initial MVP in September 2025 to enterprise-grade Spec-Kit governance and hardened autonomous multi-agent pipelines in October 2026.

---

## Executive Summary

The **Agentic Personal Porter** originated as a personal AI assistant and time-use tracking application designed to help individuals overcome cognitive fragmentation and brain fog. Over its first year ("Year 0"), the system matured through three distinct architectural generations:
1. **The Scripted Prototype Era (Fall 2025)**: Basic time logging, early CrewAI integrations, and direct Flask API scripting.
2. **The Graph & Engine Era (Spring 2026)**: Introduction of the Maslow Origin/Ambition ontology in Neo4j, MongoDB timeseries backends, and the MACH3 overhaul.
3. **The Autonomous Personas & Spec-Kit Governance Era (Summer–Fall 2026)**: Integration of autonomous agent roles (⚡ Bolt, 🎨 Palette, 🛡️ Sentinel), private brain knowledge extraction (`agentic-private-brain`), strict pre-push security hooks, and zero-cost local test architectures.

---

## 1. Genesis & The Prototype Era (September – November 2025)

The project began with an urgent focus on user introspection, objective time measurement, and combating executive dysfunction.

```
       [User Intentions]
              │
              ▼
    ┌───────────────────┐
    │ MVP Time Tracker  │ ──► [Brain Fog Metric]
    └───────────────────┘
              │
              ▼
    ┌───────────────────┐
    │  CrewAI Backend   │ ──► [Flask REST Server]
    └───────────────────┘
              │
              ▼
    ┌───────────────────┐
    │ Neo4j Integration │ ──► [Calendar Synchronization]
    └───────────────────┘
```

### Key Milestones & PRs
* **2025-09-05 (Commit `ef4c54a` / PR #1)**: *Project Inception & MVP Time Tracker*. Established initial repository structure, tracking basic user activity blocks and duration heuristics.
* **2025-09-07 (PR #2 & PR #3)**: *CrewAI & Flask Integration*. Introduced multi-agent role distribution for processing reflections, linking background workers to a local Flask API server.
* **2025-09-08 (PR #4)**: *The Brain Fog Metric*. Added algorithmic reflection scoring to evaluate user energy dips, cognitive friction, and daily fatigue patterns.
* **2025-09-19 (PR #5 & PR #6)**: *Hero's Inventory & Weekly Planner*. Transitioned from flat logs to an interactive gamified UI ("Hero's Inventory") and weekly calendar layout.
* **2025-09-23 – 2025-09-26 (PR #7)**: *Graph Database & Calendar Pipeline*. First integration of Neo4j graph nodes and Google Calendar OAuth, laying the groundwork for contextual knowledge representation.
* **2025-11-13 – 2025-11-14 (PR #8)**: *Research & Educational Agent Extension*. Early exploration of automated literature review and structured knowledge retrieval.

---

## 2. The Overhauls & Multi-Model Architecture (March – May 2026)

Following a brief hiatus, 2026 brought rapid architectural shifts toward high-reliability, production-grade cloud services and graph models.

### Key Milestones
* **March 2026 (MACH2 & Persona Experiments)**:
  * Formalized the GTKY (Get To Know You) agents: *Identity Architect*, *Librarian*, *Historian*, and *Base Classifier*.
  * Socratic mirror logic designed to gently guide reflection rather than prescribe rigid schedules.
* **April 2026 (The MACH3 Overhaul & UI Rework)**:
  * Complete overhaul of frontend styling, migrating to Tailwind CSS v4.
  * Established the **Silas Protocol** (strict security, verification gates, zero swallowed exceptions) and **Fiona Protocol** (WCAG accessibility and semantic UI standards).
* **May 2026 (FinOps & Infrastructure Guardrails)**:
  * Designed and deployed the automated GCP Billing Killswitch (`gcp-billing-killswitch`) to safeguard against infinite LLM loops and runaway cloud spend.
  * Migrated from ephemeral file storage to dual MongoDB timeseries (telemetry) and Neo4j graph schemas (entity relationships).

---

## 3. Autonomous Personas & Security Hardening (June – August 2026)

During the summer of 2026, Jules-driven development teams adopted specialized agent identities to systematically harden the platform.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Autonomous Engineering Roles                 │
├─────────────────┬─────────────────────────┬─────────────────────┤
│   ⚡ Bolt       │       🎨 Palette        │     🛡️ Sentinel     │
│ (Performance)   │     (Accessibility)     │      (Security)     │
├─────────────────┼─────────────────────────┼─────────────────────┤
│ • MongoDB batch │ • WCAG screen-reader    │ • Exception triage  │
│   projections   │   ARIA tags             │ • JWT auth defense  │
│ • Deserializer  │ • Async button loading  │ • State leak & race │
│   optimization  │   indicators            │   condition fixes   │
└─────────────────┴─────────────────────────┴─────────────────────┘
```

### Key Milestones & PRs
* **PR #63 (July 2026)**: Accessibility improvements for form labels, emojis, and screen-reader usability (🎨 Palette).
* **PR #68 (July 2026)**: MongoDB batch query optimization via projection dictionaries, slashing serialization latency (⚡ Bolt).
* **PR #74 (August 2026)**: Comprehensive unit test harness for graph data routes.
* **PR #75 & PR #76 (August 2026)**: CodeQL automated security scanning setup and URL sanitization patches.
* **PR #79 (September 2026)**: Critical fix preventing global state leakage and exception swallowing across `porter_manager.py` (🛡️ Sentinel).

---

## 4. Spec-Kit Governance & The Clean Start (September – October 2026)

In early October 2026, the project underwent its most significant operational evolution: adopting **Spec-Kit** hierarchical governance and achieving a pristine, debt-free repository state.

### Key Milestones
1. **Hierarchical Constitution**:
   * Isolated upstream organizational governance contracts inside private repository storage.
   * Enforced local project constitution in [`documentation/architecture/spec-kit-constitution.md`](./architecture/spec-kit-constitution.md).
2. **Zero-Cost Local Development**:
   * Eliminated external database reliance for testing using `mongomock` fixtures and containerized local MongoDB (`porter-mongo:7.0`).
3. **Tooling & Environment Simplification**:
   * Retired Conda; standardized 100% on `uv` (`uv.lock`, `uv run pytest`) for sub-second test execution and unified dependency trees.
4. **Complete Workspace Archival**:
   * Built compressed multi-year archives (`archive_2025.tar.gz`, `archive_2026_Q1.tar.gz`, `archive_2026_Q2.tar.gz`, `archive_2026_Q3.tar.gz`).
   * Moved all outdated architecture design documents into `.legacy_hr/2026/outdated-doc/`.
   * Standardized all active project documentation into strict `kebab-case`.

---

## Current Platform State (October 2026)

| Layer | Technology | Primary Role |
| :--- | :--- | :--- |
| **Package Manager** | `uv` (Rust) | Workspace management & dependency locking |
| **Runtime Language** | Python 3.12 | Core application services & agents |
| **Database (Graph)** | Neo4j 5.x | Maslow intention & ambition ontology |
| **Database (Doc)** | MongoDB 7.0 (Local / Mock) | Calendar timeseries & raw activity store |
| **Vector Index** | Weaviate Client | Private brain semantic retrieval |
| **Frontend** | Vanilla JS / Tailwind CSS v4 | Lightweight, zero-build UI |
| **Security Gates** | CodeQL + Git Pre-push Hook | Secret scanning & OWASP verification |
