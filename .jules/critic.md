# Critic's Journal - Critical Learnings & Operational Playbook

This document is a living record of critical learnings, adversarial vulnerability patterns, edge cases, and failure mode analyses accumulated during stress-testing and architectural review of the personal porter application.

## 2026-10-11 - Hostile Boundary Inputs and Type Coercion Exploits
**Learning:** Assuming that incoming query parameters, JSON payloads, or calendar summary fields conform to expected types allows malformed, oversized, or nested payloads to trigger unexpected unhandled exceptions (500s) or crash worker processes.
**Action:** Actively formulate adversarial test fixtures injecting null bytes, extreme string lengths (100k+ chars), deeply nested JSON objects, negative timestamps, and non-UTF8 sequences into every endpoint to ensure graceful 400 Bad Request handling.

## 2026-10-11 - Concurrent Race Conditions and Cursor Re-entrancy
**Learning:** Asynchronous or multi-threaded background workers accessing the same MongoDB collection or local state cache without concurrency controls or locking can double-process tasks or operate on exhausted database cursors.
**Action:** Audit and stress-test all multi-event sync and bulk processing loops with concurrent mock runs. Verify that cursors are cast to lists before re-attempt loops and idempotency keys are enforced on all write paths.

## 2026-10-11 - Questioning Unjustified Architectural Assumptions
**Learning:** Optimistic assumptions—such as assuming external APIs (Google Calendar, Gemini LLM) will respond in under 2 seconds, never return empty payloads, or never rate-limit with 429s—lead to cascading timeouts and frontend hangs.
**Action:** Subject every new architecture proposal to an adversarial pre-mortem. Enforce circuit breakers, exponential backoff with jitter, strict timeout deadlines, and clear fallback user feedback for all downstream integrations.
