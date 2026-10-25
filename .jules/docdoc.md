# DocDoc's Journal - Critical Learnings & Operational Playbook

This document is a living record of critical learnings, knowledge curation workflows, Spec-Kit stewardship rules, and documentation hygiene governed by the user's shared project governance standards.

## 2026-10-11 - Strict Kebab-Case Directory and File Routing
**Learning:** Inconsistent casing (e.g. `Documentation/` vs `documentation/`, `ARCHITECTURE.md` vs `architecture.md`, `quick_start.md` vs `quick-start.md`) causes broken markdown cross-references and filesystem confusion on case-sensitive Linux platforms.
**Action:** Enforce strict lowercase `kebab-case` for all documentation files and directories under `documentation/`. The only markdown files permitted in the repository root are `README.md` and `AGENTS.md` (the universal Rosetta Stone root contract for Google Jules and CLI agents).

## 2026-10-11 - Zero-Deletion Governance and Legacy Vault Isolation
**Learning:** Hard-deleting historical files risks losing domain rationale and historical context, while leaving stale files or `.bk` backup files scattered across source directories confuses search tools and pollutes AI context windows.
**Action:** Never permanently delete code or documentation. Always move obsolete files into `.legacy_hr/` (partitioned by year/context). Ensure `.legacy_hr/` is ignored by both `.gitignore` and `.geminiignore`. Automatically move lingering `.bk` files into `.legacy_hr/` upon task completion.

## 2026-10-11 - Living Chronicles and Architecture Synchronization
**Learning:** Static documentation rapidly goes stale unless tied into release workflows, and research artifacts left in local scratch paths are unavailable to peer agents.
**Action:** Maintain a living chronicle in `documentation/year0.md` capturing architectural breakthroughs. Upon task completion, synchronize finalized documentation and execute `scripts/analyze_scripts/verify_doc_hygiene.py`.

## 2026-10-17 - Shared User Governance & Project Spec-Kit Stewardship
**Learning:** Without a clear alignment between universal user governance invariants and project-specific architecture contracts, agent instructions drift or duplicate boilerplate rules.
**Action:** Maintain `.specify/memory/constitution.md` and `AGENTS.md` so they inherit the user's universal project governance (Zero-Trust `.auth/`, FinOps killswitches, mock-first TDD, `.legacy_hr/` archival, `kebab-case` docs, and 40-char SHA-pinned workflows) alongside project-specific domain contracts, data schemas, and port topologies.

## 2026-10-17 - Cross-Surface Agent Synchronization
**Learning:** Antigravity CLI (`agy`) and Google Jules (`@google/jules`) ingest context through both local `.agents/` configurations and root `AGENTS.md` / `.jules/*.md` playbooks.
**Action:** Whenever updating project governance or persona definitions:
1. Keep root `AGENTS.md` and `.jules/*.md` synchronized with active domain tasks.
2. Sync `.agents/agents/*.md` and `.jules/*.md` to `~/.gemini/config/` via `uv run python scripts/porter_cli_agents.py sync`.
3. Run `uv run python scripts/porter_cli_agents.py verify docdoc` to verify documentation hygiene.
