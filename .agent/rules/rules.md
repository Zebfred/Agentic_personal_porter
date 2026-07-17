---
trigger: always_on
---

# Rules for Agentic Personal Porter

## 1. File, Handoff & Documentation Hygiene

### Markdown & Project Documentation
* **CRITICAL Location:** All markdown (`.md`) documentation files MUST be placed in the `Documentation/` directory. 
* **Project Root:** Never create markdown files in the project root. The only exception is `README.md`.
* **Automatic Routing:** If asked or required to create documentation, automatically place it in `Documentation/` (e.g. `Documentation/[FILENAME].md`) without asking.
* **Examples:**
  * ✅ `Documentation/ARCHITECTURE.md`
  * ❌ `ARCHITECTURE.md` (in root)
* **When to Create Documentation:** Implementation summaries, setup guides, architecture details, API specs, troubleshooting guides, and explanatory markdown files.

### File Retentions & Backups
* **Backup Creation:** Always create backups for all files changed (e.g. appending a `.bk` extension).
* **No File Deletion:** Never permanently delete files. All outdated files must be moved to the `.legacy_hr/` directory at the project root.
* **Token Context Hygiene:** Ensure `.legacy_hr/` remains in `.gitignore` and `.cursorignore` to prevent old code from polluting the AI token context window.
* **Mandatory Cleanup:** Upon task completion, independently move any lingering `.bk` files into the `.legacy_hr/` directory rather than leaving them scattered in active directories.

### Temporary File & Log Management
* **File Extensions:** Any temporary logs, run captures, or debugging logs generated during development or agent operations MUST use the `.log` extension to ensure they are automatically ignored by Git (per the `*.log` rule in `.gitignore`).
* **Directory Scoping:** Alternatively, place temporary logs in the `logs/` directory or scratch files in the `scratch/` directory, which are both configured to be ignored by Git.

### Private Brain Submodule & Artifact Sync
* **Export Artifacts:** Upon task completion, the agent MUST automatically copy the finalized `task.md` and `walkthrough.md` artifacts into the `Agentic_Private_Brain/Completed_Tasks/` directory.
* **Artifact Naming:** The files should be renamed to include the current date and a descriptive name using the format: `YYYY-MM-DD_Task_Name_Task.md` and `YYYY-MM-DD_Task_Name_Walkthrough.md`.
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
* **Environment Manager:** Use the conda environment (`conda activate agentic_porter`).
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
* **Scope Definition:** Agent chats will individually be responsible for doing development in exactly one domain as outlined in their respective `Documentation/Current_work/ACTIVE_[Domain].md` document.
* **Pre-flight Check:** At the start of every session, the assigned agent MUST independently read their specific ACTIVE document before proposing any code edits.
* **Verification Log:** As tasks are performed, the ACTIVE document must be updated to note human verification of completion.

### Testing & Verification
* **Definition of Done:** Task completion strictly requires running a verification script, test suite, or completing a checklist.
* **Test Hygiene:** Run tests before committing major changes. Update tests when modifying functionality. Keep test files organized in the `tests/` directory.
* **Git Workflow:** Create feature branches for significant changes, use descriptive commit messages, and test thoroughly before merging to main.