# DocDoc's Journal - Critical Learnings & Operational Playbook

This document is a living record of critical learnings, knowledge curation workflows, Spec-Kit stewardship rules, and documentation hygiene accumulated across `Notes_repo` and `Agentic_personal_porter`.

## 2026-10-11 - Strict Kebab-Case Directory and File Routing
**Learning:** Inconsistent casing (e.g. `Documentation/` vs `documentation/`, `ARCHITECTURE.md` vs `architecture.md`, `quick_start.md` vs `quick-start.md`) causes broken markdown cross-references and filesystem confusion on case-sensitive Linux platforms.
**Action:** Enforce strict lowercase `kebab-case` for all documentation files and directories under `documentation/`. The only markdown files permitted in the repository root are `README.md` and `AGENTS.md` (the universal Rosetta Stone root contract for Google Jules and CLI agents).

## 2026-10-11 - Zero-Deletion Governance and Legacy Vault Isolation
**Learning:** Hard-deleting historical files risks losing domain rationale and historical context, while leaving stale files or `.bk` backup files scattered across source directories confuses search tools and pollutes AI context windows.
**Action:** Never permanently delete code or documentation. Always move obsolete files into `.legacy_hr/` (partitioned by year/context). Ensure `.legacy_hr/` is ignored by both `.gitignore` and `.geminiignore`. Automatically move lingering `.bk` files into `.legacy_hr/` upon task completion.

## 2026-10-11 - Living Chronicles and Private Brain Synchronization
**Learning:** Static documentation rapidly goes stale unless tied into release workflows, and research artifacts left in local scratch paths are unavailable to peer agents.
**Action:** Maintain a living chronicle in `documentation/year0.md` (in project repos) or `Projects/<project>/synopsis/` (in `Notes_repo`) capturing architectural breakthroughs. Upon task completion, synchronize finalized artifacts and execute verification gates.

## 2026-10-17 - Two-Tier Company & Project Spec-Kit Stewardship
**Learning:** Without a clear separation between enterprise-wide invariants and project-specific architecture contracts, agent instructions drift across repositories or duplicate boilerplate rules.
**Action:** Curate specifications in a strict 2-Tier hierarchy:
1. **Level 0 (Company Spec Kit — `Companies/Nexus_Constitution.md`)**: Universal non-negotiable policies (Zero-Trust `.auth/`, FinOps killswitches, mock-first TDD, `.legacy_hr/`, `kebab-case` docs, SHA-pinned workflows).
2. **Level 1 (Project Spec Kits — `Projects/<project>/spec-kit.md`, `Projects/<project>/playbook.md`, & `.specify/memory/constitution.md`)**: Project-specific domain contracts, data schemas, port topologies, and Spec-Driven Development (`specify`) artifacts that inherit Level 0.

## 2026-10-17 - 3-Layer "Rosetta Stone" Synchronization Across Agent Surfaces
**Learning:** Antigravity CLI (`agy`), Google Jules (`@google/jules`), and Gemini Web Browser Gems ingest context through different mechanisms (local `.agents/skills/` & MCP vs. cloud-cloned root `AGENTS.md` vs. single-file Gem knowledge uploads).
**Action:** Whenever curating knowledge or updating rules/specs in `Notes_repo`, synchronize all three layers:
1. Update `AGENTS.md` (Surface 2: Google Jules root contract).
2. Sync `.agents/skills/` junctions and `.agents/agents/` to `~/.gemini/config/` via `scripts/sync_rosetta_skills.ps1` and `scripts/porter_cli_agents.py sync` (Surface 1: `agy` CLI / IDE).
3. Run `uv run python scripts/build_context_pack.py` to compile `Vault/gemini-web-context-pack.md` and verify zero secret leaks via `uv run python scripts/verify_kb.py` (Surface 3: Gemini Web Browser Gem).
