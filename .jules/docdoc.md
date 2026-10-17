# DocDoc's Journal - Critical Learnings & Operational Playbook

This document is a living record of critical learnings, governance rules, and documentation hygiene accumulated during the development and maintenance of the personal porter application.

## 2026-10-11 - Strict Kebab-Case Directory and File Routing
**Learning:** Inconsistent casing (e.g. `Documentation/` vs `documentation/`, `ARCHITECTURE.md` vs `architecture.md`, `quick_start.md` vs `quick-start.md`) causes broken markdown cross-references and filesystem confusion on case-sensitive Linux platforms.
**Action:** Enforce strict lowercase `kebab-case` for all documentation files and directories under `documentation/`. The only markdown file permitted in the project root is `README.md`.

## 2026-10-11 - Zero-Deletion Governance and Legacy Vault Isolation
**Learning:** Hard-deleting historical files risks losing domain rationale and historical context, while leaving stale files or `.bk` backup files scattered across source directories confuses search tools and pollutes AI context windows.
**Action:** Never permanently delete code or documentation. Always move obsolete files into `.legacy_hr/` (partitioned by year and quarter). Ensure `.legacy_hr/` is ignored by both `.gitignore` and `.geminiignore`. Automatically move lingering `.bk` files into `.legacy_hr/` upon task completion.

## 2026-10-11 - Living Chronicles and Private Brain Synchronization
**Learning:** Static documentation rapidly goes stale unless tied into release workflows, and research artifacts left in local scratch paths are unavailable to peer agents.
**Action:** Maintain a living chronicle in `documentation/year0.md` capturing architectural breakthroughs. Upon task completion, copy finalized `task.md` and `walkthrough.md` artifacts into `agentic-private-brain/completed-tasks/` and execute `make sync-brain`.
