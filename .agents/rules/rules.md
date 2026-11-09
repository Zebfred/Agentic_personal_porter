---
trigger: always_on
---

# Rules for Agentic Personal Porter

## 1. File, Handoff & Documentation Hygiene

### Markdown & Project Documentation
* **CRITICAL Location:** All markdown (`.md`) documentation files MUST be placed in the `documentation/` directory (lowercase).
* **Kebab-Case Naming Standard:** All markdown files MUST use `kebab-case` naming (e.g. `quick-start.md`, `spec-kit-constitution.md`, `active-backend-tasks.md`). The only exception is `README.md`.
* **Project Root:** Never create markdown files in the project root. The only exception is `README.md`.
* **Automatic Routing:** If asked or required to create documentation, automatically place it in `documentation/` using kebab-case (e.g. `documentation/[category]/[file-name].md`) without asking.
* **Examples:**
  * ✅ `documentation/architecture/spec-kit-constitution.md`
  * ✅ `documentation/development/quick-start.md`
  * ❌ `Documentation/...` (capitalized directory)
  * ❌ `documentation/ARCHITECTURE.md` (UPPERCASE filename)
  * ❌ `documentation/quick_start.md` (snake_case filename)
  * ❌ `quick-start.md` (in root)
* **When to Create Documentation:** Implementation summaries, setup guides, architecture details, API specs, troubleshooting guides, and explanatory markdown files.

### File Retentions & Backups
* **Backup Creation:** Always create backups for all files changed (e.g. appending a `.bk` extension).
* **No File Deletion:** Never permanently delete files. All outdated files must be moved to the `.legacy_hr/` directory at the project root.
* **Token Context Hygiene:** Ensure `.legacy_hr/` remains in `.gitignore` and `.geminiignore` to prevent old code from polluting the AI token context window.
* **Mandatory Cleanup:** Upon task completion, independently move any lingering `.bk` files into the `.legacy_hr/` directory rather than leaving them scattered in active directories.

### Temporary File & Log Management
* **File Extensions:** Any temporary logs, run captures, or debugging logs generated during development or agent operations MUST use the `.log` extension to ensure they are automatically ignored by Git (per the `*.log` rule in `.gitignore`).
* **Directory Scoping:** Alternatively, place temporary logs in the `logs/` directory or scratch files in the `scratch/` directory, which are both configured to be ignored by Git.

### Private Brain Submodule & Artifact Sync
* **Export Artifacts:** Upon task completion, the agent MUST automatically copy the finalized `task.md` and `walkthrough.md` artifacts into the `agentic-private-brain/completed-tasks/` directory.
* **Artifact Naming:** The files should be renamed to include the current date and a descriptive name in kebab-case using the format: `YYYY-MM-DD-task-name-task.md` and `YYYY-MM-DD-task-name-walkthrough.md`.
* **Sync Private Brain:** After finalizing artifacts or writing new deployment scripts into the private brain, the agent MUST execute `make sync-brain` to commit and push changes to the remote repository.

---

## 2. Code Quality & Standards

### Project Structure & Imports
* **Absolute Imports:** Always use absolute imports with the `src.` prefix when importing from the main application (e.g., `from src.main import run_crew`).
* **Path Resolution:** Add the project root to `sys.path` in entry-point files (like `src/app.py`) to support direct execution.
* **Directory Layout:**
  * Main application code: `src/`
  * Frontend assets: `frontend/`
  * RAG system: `rag_system/`
  * Scripts: `scripts/`
  * Tests: `tests/`

### Python Standards & Error Handling
* **Style:** Follow PEP 8 guidelines. Use type hints, f-strings, and clear variable/function names.
* **Documentation:** Add docstrings to all functions and classes.
* **Error Handling:** Provide clear, actionable error messages. Include traceback details for debugging in development and return appropriate HTTP status codes.

### Environment & Dependencies
* **Environment Manager:** Use the `uv` package manager (`uv run ...`, `uv sync`) with the project virtual environment (`.venv`).
* **Package Manager:** Use `uv` package manager workspaces (`pyproject.toml`).
* **Google Cloud SDK:** Use for interacting with GCP services.
* **Make:** Use for running common development tasks (defined in the `Makefile`).
* **Private Brain & Vector Search:** Use the **Weaviate** database client (`weaviate-client`) for semantic lookup and indexing of the private brain knowledge bases. Avoid raw file reads where Weaviate vector lookup is applicable.

### Styling & CSS Compiling
* **Tailwind CSS Version:** Use **Tailwind CSS v4** (via `@tailwindcss/cli`) for compiling frontend stylesheets.
* **Build Target:** Run `make build-css` (which executes `npm run build:css` to compile `./frontend/css/input.css` to `./frontend/css/style.css`).

---

## 3. Workflow, Testing & Verification

### Strict Domain Scoping
* **Scope Definition:** Agent chats will individually be responsible for doing development in exactly one domain as outlined in their respective `documentation/current-work/active-[domain].md` document.
* **Pre-flight Check:** At the start of every session, the assigned agent MUST independently read their specific ACTIVE document before proposing any code edits.
* **Verification Log:** As tasks are performed, the ACTIVE document must be updated to note human verification of completion.

### Testing, Verification & 3-Tier Stacked PR Git Workflow
* **Definition of Done:** Task completion strictly requires running a verification script, test suite, or completing a checklist (`make verify-done`).
* **Test Hygiene:** Run tests before committing major changes. Update tests when modifying functionality. Keep test files organized in the `tests/` directory.
* **3-Tier Branch & Worktree Topology:**
  1. **Protected Release Branch (`main`)**: Never commit or push directly to `main`.
  2. **Working Branch (`dev` or `dev/<domain>`)**: Shared machine-agnostic integration branch kept synced with `main` via `.github/workflows/sync-working-branches.yml`.
  3. **Topic Branches & Git Worktrees (`feat/<topic>`, `fix/<topic>`, `chore/<topic>`)**: Branch off the working branch or create a dedicated Git worktree (`git worktree add ../<repo>-<topic> -b feat/<topic> <working-branch>`) for concurrent work.
* **35-File Stacked PR Limit (`MAX_PR_FILES = 35`):**
  * Pull Requests must **never exceed 35 changed files** (`<= 35` files).
  * When a feature or refactor requires `> 35` file changes, split the work into an ordered **PR Stack** (`base <- part1 <- part2 <- part3`, `<= 35` files per PR) using `gh pr create --base <prev-branch> --head <next-branch> --fill`.
  * Use `make pr-check` to validate branch & file count before opening or updating a PR with `make pr-create`.

### GitHub Actions Security
* **Pin Actions to SHA:** Always pin GitHub Actions to an immutable 40-character commit SHA (e.g., `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683` instead of `@v4`) to protect the CI pipeline against supply chain attacks where tag references can be maliciously updated. Always add a comment noting the version name (e.g. `# v4.2.2`).