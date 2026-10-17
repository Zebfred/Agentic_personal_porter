# Archie's Journal - Critical Learnings & Operational Playbook

This document is a living record of critical learnings, architectural insights, and modular structural patterns accumulated during the design and maintenance of the personal porter application.

## 2026-10-11 - Contract-First Typing with Pydantic v2
**Learning:** Allowing dictionary payloads without formal schema validation to propagate from Flask request handlers directly into database persistence layers leads to data drift, silent key mismatches, and fragile coupling between routes and storage.
**Action:** Always define explicit Pydantic v2 request/response models in `src/schemas/` before writing route handlers or database operations. Validate inputs at the boundary and serialize outputs consistently.

## 2026-10-11 - Modular Decoupling and Domain Boundary Integrity
**Learning:** Direct cross-domain imports (such as importing frontend view logic into backend database services or importing RAG vector search clients directly inside lightweight calendar sync routines) create circular dependencies and monolithic entanglement.
**Action:** Maintain clean dependency layering: `src/core/` (foundational domain primitives) <- `src/database/` (data access) <- `src/services/` (business logic) <- `src/blueprints/` (HTTP/API entrypoints). Never allow circular imports or cross-domain leaks.

## 2026-10-11 - Elimination of Orphaned and Dead Logic (Slop Defense)
**Learning:** Commented-out obsolete endpoints, lingering print statements, and dead legacy utility functions degrade developer velocity and increase cognitive load across multi-agent workflows.
**Action:** Enforce strict AST linting with ruff rules (`E`, `F`, `B`, `C4`, `T20`). Delete unused imports and dead functions immediately; rely on Git history and `.legacy_hr/` rather than in-tree commented-out code.
