#!/usr/bin/env python3
"""Standardized Git Hooks Runner (git_hooks_runner.py).

Provides fast, cross-platform (`pwsh` / `bash` / Git for Windows) execution for:
1. `pre-commit` (< 1 second, staged files only):
   - Auto-sweeps stray *.bk* files into .legacy_hr/hook_backups/.
   - Blocks committing files inside .auth/, .legacy_hr/, or *.bk* / *.pyc files.
   - Scans staged diff lines (+...) for plaintext secrets/tokens (Sentinel 🛡️).
   - Verifies root markdown boundary (README.md, AGENTS.md) and lowercase kebab-case in documentation/ (DocDoc 📚).
   - Blocks hardcoded OS absolute paths (C:\\Users\\..., /home/..., file:///C:/...) and sensitive log/env files.
   - Lints staged Python files with `ruff check` and staged JS files with `node -c` when present (Archie 🏛️ & Jovol ⚛️).
2. `pre-push` (Silas 🏛️ Constitutional Gate):
   - Runs verify_doc_hygiene.py, ruff check src tests, and fast unit tests (pytest tests/unit).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

from agent_lifecycle_hooks import (
    ABSOLUTE_PATH_PATTERNS,
    SAFE_PLACEHOLDERS,
    SECRET_PATTERNS,
    sweep_stray_backups,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def resolve_git_bin() -> str:
    """Resolve git executable across system PATH and standard Windows install locations."""
    found = shutil.which("git")
    if found:
        return found
    win_git = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "cmd" / "git.exe"
    if win_git.exists():
        return str(win_git)
    return "git"


def resolve_repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parents[1]


def get_staged_files(repo_root: Path) -> List[str]:
    """Return list of staged file paths (Added, Copied, Modified, Renamed)."""
    res = subprocess.run(
        [resolve_git_bin(), "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if res.returncode != 0:
        return []
    return [line.strip() for line in res.stdout.splitlines() if line.strip()]


def scan_staged_diff_secrets_and_paths(repo_root: Path) -> List[str]:
    """Scan added lines in `git diff --cached` for plaintext credentials and hardcoded OS absolute paths."""
    res = subprocess.run(
        [resolve_git_bin(), "diff", "--cached", "-U0"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if res.returncode != 0:
        return []

    violations: List[str] = []
    current_file = "unknown"
    skip_files = {
        "agent_lifecycle_hooks.py",
        "git_hooks_runner.py",
        "verify_doc_hygiene.py",
        "verify_kb.py",
        "build_context_pack.py",
    }

    for line in res.stdout.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            continue
        if Path(current_file).name in skip_files:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added_text = line[1:]
            if any(marker in added_text for marker in SAFE_PLACEHOLDERS):
                continue
            for pattern, label in SECRET_PATTERNS:
                if re.search(pattern, added_text):
                    violations.append(f"[{label}] in staged file '{current_file}': {added_text.strip()[:80]}")
            for pattern, label in ABSOLUTE_PATH_PATTERNS:
                if re.search(pattern, added_text):
                    violations.append(
                        f"[{label}] in staged file '{current_file}': {added_text.strip()[:80]} "
                        f"(use project-relative paths instead)"
                    )
    return violations


def run_pre_commit(repo_root: Path) -> int:
    """Execute sub-second pre-commit checks on staged files."""
    print("🛡️  [Nexus Git Hook] Running pre-commit checks...")

    # 1. Sweep stray .bk* files into .legacy_hr/hook_backups/
    swept = sweep_stray_backups(repo_root)
    if swept > 0:
        print(f"   📦 Auto-archived {swept} stray .bk backup file(s) into .legacy_hr/hook_backups/")

    staged = get_staged_files(repo_root)
    if not staged:
        print("   ✅ No staged files to check.")
        return 0

    errors: List[str] = []
    staged_py: List[str] = []
    staged_js: List[str] = []
    forbidden_filenames = {".env", "credentials.json", "token.json", "token.pickle", "config.local.js"}

    for rel_path in staged:
        norm_path = rel_path.replace("\\", "/")
        parts = norm_path.split("/")
        filename = parts[-1]

        # 2. Forbidden staged paths (.auth/, .legacy_hr/, *.bk*, *.pyc, *.log, *.pem, .env*)
        if parts[0] in {".auth", ".legacy_hr", "logs"}:
            errors.append(f"Forbidden directory staged for commit: '{norm_path}' (must remain gitignored).")
        if ".bk" in filename or filename.endswith(".pyc") or "__pycache__" in parts:
            errors.append(f"Forbidden backup or cache artifact staged: '{norm_path}'.")
        if (
            filename in forbidden_filenames
            or filename.startswith(".env")
            or filename.endswith((".log", ".pem", ".key", ".pickle"))
        ):
            errors.append(f"Forbidden sensitive or runtime log file staged: '{norm_path}'.")

        # 3. Root markdown & documentation/ kebab-case check
        if len(parts) == 1 and filename.lower().endswith(".md"):
            if filename not in {"README.md", "AGENTS.md"}:
                errors.append(
                    f"Unauthorized root Markdown file staged: '{filename}'. Only README.md and AGENTS.md are allowed at root."
                )
        if parts[0].lower() == "documentation":
            for sub_dir in parts[1:-1]:
                if any(c.isupper() for c in sub_dir) or "_" in sub_dir:
                    errors.append(f"Non-kebab-case directory in documentation/: '{norm_path}'")
            if filename.lower().endswith(".md"):
                stem = Path(filename).stem
                if any(c.isupper() for c in stem) or "_" in stem:
                    errors.append(f"Non-kebab-case Markdown file in documentation/: '{norm_path}'")

        if filename.endswith(".py") and (repo_root / rel_path).exists():
            staged_py.append(rel_path)
        if filename.endswith(".js") and (repo_root / rel_path).exists():
            staged_js.append(rel_path)

    # 4. Staged diff secret & hardcoded absolute path scan
    diff_hits = scan_staged_diff_secrets_and_paths(repo_root)
    errors.extend(diff_hits)

    # 5. Fast staged Ruff lint (when pyproject.toml / src exists in code repos)
    if staged_py and (repo_root / "pyproject.toml").exists():
        uv_bin = shutil.which("uv")
        if uv_bin:
            res = subprocess.run(
                [uv_bin, "run", "ruff", "check", *staged_py],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if res.returncode != 0:
                errors.append(f"Ruff lint failed on staged Python files:\n{res.stdout or res.stderr}")

    # 6. Fast staged JS syntax check (node -c)
    if staged_js:
        node_bin = shutil.which("node") or shutil.which("node.exe")
        if node_bin:
            for js_file in staged_js:
                res = subprocess.run(
                    [node_bin, "-c", js_file],
                    cwd=str(repo_root),
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                if res.returncode != 0:
                    errors.append(f"JavaScript syntax check (node -c) failed for '{js_file}':\n{res.stderr or res.stdout}")

    if errors:
        print("\n❌ [Pre-Commit BLOCKED] Please fix the following issues before committing:")
        for err in errors:
            print(f"   • {err}")
        return 1

    print(f"   ✅ pre-commit passed ({len(staged)} staged file(s) verified).")
    return 0


def run_pre_push(repo_root: Path) -> int:
    """Execute Silas Constitutional Verification Gate before git push."""
    print("🏛️  [Silas pre-push Gate] Verifying repository quality gates before push...")
    swept = sweep_stray_backups(repo_root)
    if swept > 0:
        print(f"   📦 Auto-archived {swept} stray .bk backup file(s) into .legacy_hr/hook_backups/")

    # Check root markdown boundary (only README.md and AGENTS.md allowed at root)
    allowed_root = {"README.md", "AGENTS.md"}
    for root_md in repo_root.glob("*.md"):
        if root_md.name not in allowed_root:
            print(f"   ❌ Unauthorized root Markdown file: {root_md.name} (Only README.md and AGENTS.md allowed)")
            return 1

    doc_hygiene = repo_root / "scripts" / "analyze_scripts" / "verify_doc_hygiene.py"
    if doc_hygiene.exists():
        res_doc = subprocess.run([sys.executable, str(doc_hygiene)], cwd=str(repo_root), check=False)
        if res_doc.returncode != 0:
            return res_doc.returncode

    uv_bin = shutil.which("uv")
    if uv_bin and (repo_root / "src").exists():
        if (repo_root / "tests" / "unit").exists():
            print("   ▶ Running fast unit test suite (tests/unit)...")
            env = os.environ.copy()
            env.setdefault("PROJECT_ID", "test-project")
            env["DISABLE_CLOUD_LOGGING"] = "true"
            res_pytest = subprocess.run(
                [uv_bin, "run", "pytest", "tests/unit", "-q", "--tb=short"],
                cwd=str(repo_root),
                env=env,
                check=False,
            )
            if res_pytest.returncode != 0:
                return res_pytest.returncode

    print("   ✅ Silas pre-push verification gate passed!")
    return 0


def install_git_hooks(repo_root: Path) -> int:
    """Configure git core.hooksPath to .githooks and ensure hook scripts are executable."""
    githooks_dir = repo_root / ".githooks"
    if not githooks_dir.exists():
        print(f"❌ .githooks directory not found in {repo_root}", file=sys.stderr)
        return 1

    res = subprocess.run(
        [resolve_git_bin(), "config", "core.hooksPath", ".githooks"],
        cwd=str(repo_root),
        check=False,
    )
    if res.returncode != 0:
        print("❌ Failed to set git config core.hooksPath .githooks", file=sys.stderr)
        return res.returncode

    git_hooks_legacy = repo_root / ".git" / "hooks"
    for hook_name in ("pre-commit", "pre-push"):
        hook_file = githooks_dir / hook_name
        if hook_file.exists():
            try:
                hook_file.chmod(0o755)
                if git_hooks_legacy.exists():
                    shutil.copy2(hook_file, git_hooks_legacy / hook_name)
            except OSError:
                pass

    print(f"✅ Configured git core.hooksPath -> .githooks in {repo_root}")
    return 0


def main() -> int:
    """CLI entrypoint for git hooks runner."""
    hook = sys.argv[1].lower() if len(sys.argv) > 1 else "pre-commit"
    repo_root = resolve_repo_root()

    if hook == "pre-commit":
        return run_pre_commit(repo_root)
    if hook == "pre-push":
        return run_pre_push(repo_root)
    if hook == "install":
        return install_git_hooks(repo_root)

    print(f"Unknown hook command: {hook}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
