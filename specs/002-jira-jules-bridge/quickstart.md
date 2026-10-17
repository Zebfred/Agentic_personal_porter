# Quickstart & Validation Guide: Unified Spec-Kit, Jira, and Jules Bridge

**Feature**: `002-jira-jules-bridge`
**Date**: 2026-10-17
**Spec**: [spec.md](spec.md) | **Data Model**: [data-model.md](data-model.md) | **Contract**: [jira-jules-bridge-contract.json](contracts/jira-jules-bridge-contract.json)

---

## 1. Prerequisites & Zero-Trust Configuration (`.auth/.env`)

All external credentials reside strictly inside `.auth/.env` (**Principle I — Sovereign Privacy & Zero-Trust Security**). Add the following placeholders to `.auth/.env`:

```env
# --- Atlassian Jira Integration ---
JIRA_BASE_URL="https://your-domain.atlassian.net"
JIRA_EMAIL="your-email@example.com"
JIRA_API_TOKEN="<your_atlassian_api_token>"
JIRA_PROJECT_KEY="PORTER"
```

*(Note: All unit and contract tests in `tests/unit/` run 100% offline via `mongomock` and mocked HTTP responses, requiring no live Jira or Jules credentials.)*

---

## 2. Running Offline Verification Gates ($0.00 Cloud Cost)

Execute the push-button verification gate to validate schemas, linting, static types, and unit tests:

```bash
# 1. Run the dedicated Jira-Jules bridge unit test suite
uv run pytest tests/unit/test_jira_jules_bridge.py -v --tb=short

# 2. Run the full Silas Definition-of-Done gate
make verify-done

# 3. Run the 8-Persona Roster verification suite
make test-roster
```

**Expected Outcome**:
- `ruff check src tests` exits `0` with zero warnings.
- `mypy src` exits `0` with strict Pydantic v2 schema validation across `src/schemas/jira_models.py`.
- All unit tests pass in `< 2.0s` using `mongomock`.

---

## 3. CLI & Spec-Kit Hook Usage

### Scenario A: Preview Spec-Kit `tasks.md` → Jira Hierarchy (Dry Run)
Format the active feature (`specs/002-jira-jules-bridge/tasks.md`) into a standardized Jira Epic and child Stories/Tasks with canonical `T001`+ deduplication and automatic `.jules/<persona>.md` assignment:

```bash
uv run python -m src.orchestrators.speckit_jira_bridge \
  --feature-dir specs/002-jira-jules-bridge \
  --dry-run
```

### Scenario B: Live Push `tasks.md` → Jira Board
When `.auth/.env` contains valid Jira credentials, omit `--dry-run` (or run `make sync-jira`) to create/update the Epic and child issues idempotently:

```bash
uv run python -m src.orchestrators.speckit_jira_bridge \
  --feature-dir specs/002-jira-jules-bridge \
  --push
```

### Scenario C: Format & Dispatch a Task/Ticket to Google Jules
Generate a self-contained Jules work order bundling the Jira ticket, Spec-Kit acceptance criteria, `.jules/<persona>.md` operational rules, and `make test-<persona>` + `make verify-done` gates:

```bash
# Preview formatted Jules work order prompt (Dry Run)
uv run python -m src.orchestrators.speckit_jira_bridge \
  --feature-dir specs/002-jira-jules-bridge \
  --dispatch-task T001 \
  --dry-run

# Live dispatch to @google/jules CLI and annotate Jira issue
uv run python -m src.orchestrators.speckit_jira_bridge \
  --feature-dir specs/002-jira-jules-bridge \
  --dispatch-task T001 \
  --execute-jules
```
