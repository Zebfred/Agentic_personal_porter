# Google Jules CLI & True CLI Agents Operational Runbook

This runbook provides step-by-step operational procedures for discovering Session IDs, dispatching the 12 **Agentic Personal Porter** personas to **Google Jules CLI (`jules`)** and **Antigravity CLI (`agy`)**, pulling remote diffs, and keeping your laptop and desktop synchronized.

---

## 1. Quick Reference: Finding Session IDs

You never need to guess or manually hunt for a 19-digit Google Jules Session ID. There are three built-in ways to locate or bypass Session IDs:

### A. View Latest Session ID per Persona (`list`)
Run the main roster table to see every persona's installation status **and** its most recent remote Google Jules Session ID and status for this repository:
```powershell
uv run python scripts/porter_cli_agents.py list
```

### B. Search & Filter Remote Sessions (`jules-sessions`)
Query remote sessions across your connected repositories. The filter automatically handles `jules`'s 22-character table truncation in the `Repo` column:
```powershell
# List the 25 most recent sessions with persona tags
uv run python scripts/porter_cli_agents.py jules-sessions

# Filter by repository (works with short repo names or full <owner>/<repo> slugs)
uv run python scripts/porter_cli_agents.py jules-sessions --repo Agentic_personal_porter --limit 15

# Filter by a specific persona (e.g. bolt, sentinel, palette, archie, docdoc, dave, crii, jovol, silas)
uv run python scripts/porter_cli_agents.py jules-sessions --persona bolt

# Filter by session status (e.g. Planning, Awaiting, Completed)
uv run python scripts/porter_cli_agents.py jules-sessions --status Awaiting
```

### C. Use Persona Names Instead of Session IDs (`jules-pull` & `jules-teleport`)
Both `jules-pull` and `jules-teleport` accept **either** a numeric Session ID, a **persona name**, or `latest`:
```powershell
# Automatically resolves Bolt's latest remote Session ID and previews the diff
uv run python scripts/porter_cli_agents.py jules-pull bolt

# Apply Bolt's latest remote patch and automatically run Bolt's local verification gate
uv run python scripts/porter_cli_agents.py jules-pull bolt --apply --verify bolt

# Or pass an explicit numeric Session ID
uv run python scripts/porter_cli_agents.py jules-pull <SESSION_ID> --apply --verify bolt
```

---

## 2. Dispatching Personas to Google Jules (`jules`)

### Why We Use the Direct Native `jules` Binary Instead of `jules.cmd`
On Windows, the `@google/jules` npm wrapper (`run.cjs`) checks for a file named `jules` (without `.exe`), fails to find it, and re-downloads/unpacks the release archive into `%TEMP%/jules_tmp` on **every invocation**. Launching multiple `jules.cmd` processes simultaneously causes file-lock collisions (`Error: spawn EBUSY`).

`scripts/porter_cli_agents.py` caches and invokes the compiled native binary (`~/.gemini/config/bin/jules.exe`) directly, running ~10x faster and enabling true parallel dispatch.

### Dispatch a Single Persona (`jules-dispatch`)
Every persona in `scripts/porter_persona_roster.py` includes a built-in constitutional audit task (`default_task`), so the task string is optional:
```powershell
# Preview the composite prompt (1-line signature + task + .agents/agents/<name>.md + .jules/<name>.md)
uv run python scripts/porter_cli_agents.py jules-dispatch archie --dry-run

# Dispatch Archie with his default contract-first Pydantic v2 & decoupling audit task
uv run python scripts/porter_cli_agents.py jules-dispatch archie

# Dispatch Jovol with a custom task
uv run python scripts/porter_cli_agents.py jules-dispatch jovol "Audit Spec Kit primitives and add missing aria-labels"
```

### Dispatch Multiple Personas in Parallel (`jules-dispatch-batch`)
Use `jules-dispatch-batch` to launch multiple personas concurrently via `ThreadPoolExecutor`:
```powershell
# Dispatch specific personas in parallel
uv run python scripts/porter_cli_agents.py jules-dispatch-batch docdoc dave crii jovol

# Dispatch all 5 newly added personas (archie, docdoc, dave, crii, jovol) in parallel
uv run python scripts/porter_cli_agents.py jules-dispatch-batch new

# Dispatch all 8 Jules quality personas in parallel
uv run python scripts/porter_cli_agents.py jules-dispatch-batch roster
```

> [!IMPORTANT]
> **Unpushed Local Branch Protection**: When `jules new` runs inside a local Git repository, it inspects the current local branch (`git branch --show-current`) and asks Google Jules Cloud to clone that branch from GitHub. If your current local branch (e.g. `feat/true-cli-jules-agents`) has not been pushed to `origin` yet, `scripts/porter_cli_agents.py` automatically dispatches from a neutral working directory so Google Jules Cloud clones the remote repository's default branch instead of failing with a branch-not-found error. Once you push your dev branch to `origin`, it automatically dispatches against your pushed dev branch.

---

## 3. Local Verification Gates & Cross-Machine Synchronization

### Run Local Persona Verification Gates (`verify`)
```powershell
# Verify a single persona locally
uv run python scripts/porter_cli_agents.py verify jovol
uv run python scripts/porter_cli_agents.py verify dave
uv run python scripts/porter_cli_agents.py verify docdoc

# Run all 8 Jules persona gates or Silas's full gatekeeper suite
uv run python scripts/porter_cli_agents.py verify roster
uv run python scripts/porter_cli_agents.py verify silas
```

### Sync Between Project and System Config (`sync`)
Synchronizes `.agents/agents/*.md`, `.jules/*.md`, `porter_cli_agents.py`, and `porter_persona_roster.py` with `~/.gemini/config/` (archiving any overwritten `.bk` files into `.legacy_hr/cli_agent_sync_backups/`):
```powershell
uv run python scripts/porter_cli_agents.py sync --direction both
```
