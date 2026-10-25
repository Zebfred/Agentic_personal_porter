#!/usr/bin/env python3
"""Standardized Git Hooks Runner (git_hooks_runner.py).

Executes cross-platform `pre-commit` and `pre-push` gates (< 200L script, < 60L functions),
enforcing `codespell`, `black`, `ruff`, `bandit` (`[tool.bandit]`), `SKILL001`-`SKILL006`, `mypy`, and `pytest`.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Sequence

from agent_lifecycle_hooks import SAFE_PLACEHOLDERS, SECRET_PATTERNS, sweep_stray_backups

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

MAX_SCRIPT_LINES = 200


def _sanitize_error_for_logging(message: str) -> str:
    """Redact secret-like fragments before writing hook diagnostics to stdout."""
    redacted = message
    for pattern in SECRET_PATTERNS:
        try:
            redacted = re.sub(pattern, "[REDACTED_SECRET]", redacted, flags=re.IGNORECASE)
        except re.error:
            # Be defensive: malformed patterns must not break hook execution.
            continue
    redacted = re.sub(
        r"(?i)\b(password|passwd|token|secret|api[_-]?key|access[_-]?key)\b\s*[:=]\s*([^\s,;]+)",
        r"\1=[REDACTED_SECRET]",
        redacted,
    )
    return redacted
MAX_FUNCTION_LINES = 60
LEGACY_EXEMPT_SCRIPTS = {"porter_cli_agents.py"}


def resolve_repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parents[1]


def _run_cmd(args: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command and capture UTF-8 output."""
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)


def scan_staged_diff_secrets(repo_root: Path) -> List[str]:
    """Scan added lines in `git diff --cached` for plaintext credentials."""
    res = _run_cmd(["git", "diff", "--cached", "-U0"], repo_root)
    if res.returncode != 0:
        return []
    violations, current = [], "unknown"
    skip = {"agent_lifecycle_hooks.py", "git_hooks_runner.py", "verify_kb.py", "verify_doc_hygiene.py", "build_context_pack.py"}
    for line in res.stdout.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:].strip()
        elif Path(current).name not in skip and line.startswith("+") and not line.startswith("+++"):
            added = line[1:]
            if not any(m in added for m in SAFE_PLACEHOLDERS):
                for pat, label in SECRET_PATTERNS:
                    if re.search(pat, added):
                        violations.append(f"[{label}] in '{current}': {added.strip()[:80]}")
    return violations


def check_python_modularity(repo_root: Path, staged_py: Sequence[str]) -> List[str]:
    """Verify generated scripts are < 200 lines and functions are < 60 lines."""
    errors: List[str] = []
    for rel_path in staged_py:
        py_file = repo_root / rel_path
        if not py_file.exists() or py_file.name in LEGACY_EXEMPT_SCRIPTS:
            continue
        source = py_file.read_text(encoding="utf-8", errors="replace")
        line_count = len(source.splitlines())
        norm = rel_path.replace("\\", "/")
        if norm.startswith("scripts/") and line_count >= MAX_SCRIPT_LINES:
            errors.append(f"[Script Length >= {MAX_SCRIPT_LINES}L] '{norm}' has {line_count} lines (max < {MAX_SCRIPT_LINES}).")
        try:
            tree = ast.parse(source, filename=rel_path)
        except SyntaxError as exc:
            errors.append(f"[SyntaxError] '{norm}': {exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.end_lineno:
                fn_lines = node.end_lineno - node.lineno + 1
                if fn_lines >= MAX_FUNCTION_LINES:
                    errors.append(f"[Function Length >= {MAX_FUNCTION_LINES}L] '{norm}:{node.lineno}' '{node.name}' is {fn_lines}L.")
    return errors


def _run_staged_linters(repo_root: Path, staged: Sequence[str], staged_py: Sequence[str]) -> List[str]:
    """Execute codespell, black, ruff, and bandit on staged files when configured in pyproject.toml."""
    errors: List[str] = []
    pyproject, uv_bin = repo_root / "pyproject.toml", shutil.which("uv")
    if not pyproject.exists() or not uv_bin:
        return errors
    cfg = pyproject.read_text(encoding="utf-8", errors="replace")
    existing = [p for p in staged if (repo_root / p).exists() and Path(p).name != "uv.lock" and not p.endswith(".lock")]
    non_test_py = [p for p in staged_py if not p.replace("\\", "/").startswith("tests/")]
    checks = [
        ("Codespell", bool(existing) and "[tool.codespell]" in cfg, [uv_bin, "run", "codespell", *existing]),
        ("Black", bool(staged_py) and "[tool.black]" in cfg, [uv_bin, "run", "black", "--check", "--diff", *staged_py]),
        ("Ruff", bool(staged_py) and "[tool.ruff" in cfg, [uv_bin, "run", "ruff", "check", *staged_py]),
        ("Bandit", bool(non_test_py) and "[tool.bandit]" in cfg, [uv_bin, "run", "bandit", "-c", "pyproject.toml", "-q", *non_test_py]),
    ]
    for label, enabled, cmd in checks:
        if enabled:
            res = _run_cmd(cmd, repo_root)
            if res.returncode != 0:
                errors.append(f"{label} failed:\n{res.stdout or res.stderr}")
    return errors


def run_pre_commit(repo_root: Path) -> int:
    """Execute sub-second pre-commit checks on staged files."""
    print("🛡️  [Nexus Git Hook] Running pre-commit checks...")
    if sweep_stray_backups(repo_root) > 0:
        print("   📦 Auto-archived stray .bk file(s) into .legacy_hr/DDMMYYYY/")

    res = _run_cmd(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"], repo_root)
    staged = [line.strip() for line in res.stdout.splitlines() if line.strip()] if res.returncode == 0 else []
    if not staged:
        print("   ✅ No staged files to check.")
        return 0

    errors, staged_py, staged_js, touches_agents = [], [], [], False
    for rel_path in staged:
        norm, parts = rel_path.replace("\\", "/"), rel_path.replace("\\", "/").split("/")
        fname = parts[-1]
        touches_agents = touches_agents or parts[0] == ".agents"
        if parts[0] in {".auth", ".legacy_hr", ".logs"} or ".organization_discrete" in parts or ".bk" in fname or fname.endswith(".pyc"):
            errors.append(f"Forbidden path or discrete/backup artifact staged: '{norm}'.")
        if parts[0] == "data" and norm != "data/.gitkeep":
            errors.append(f"Forbidden domain data file staged in data/: '{norm}' (only data/.gitkeep may be tracked).")
        if len(parts) == 1 and fname.lower().endswith(".md") and fname not in {"README.md", "AGENTS.md"}:
            errors.append(f"Unauthorized root Markdown staged: '{fname}'.")
        if parts[0].lower() == "documentation" and fname.lower().endswith(".md") and (any(c.isupper() for c in Path(fname).stem) or "_" in Path(fname).stem):
            errors.append(f"Non-kebab-case Markdown file in documentation/: '{norm}'")
        if (repo_root / rel_path).exists():
            (staged_py if fname.endswith(".py") else staged_js if fname.endswith(".js") else []).append(rel_path)

    if touches_agents and (repo_root / "scripts" / "verify_doc_hygiene.py").exists():
        from verify_doc_hygiene import check_skill_hygiene
        errors.extend(check_skill_hygiene(repo_root))
    errors.extend(scan_staged_diff_secrets(repo_root) + check_python_modularity(repo_root, staged_py) + _run_staged_linters(repo_root, staged, staged_py))
    node_bin = shutil.which("node") or shutil.which("node.exe")
    for js_file in staged_js if node_bin else []:
        if _run_cmd([node_bin, "-c", js_file], repo_root).returncode != 0:  # type: ignore[list-item]
            errors.append(f"JavaScript syntax check (node -c) failed for '{js_file}'.")

    if errors:
        safe_errors = [_sanitize_error_for_logging(err) for err in errors]
        print("\n❌ [Nexus pre-commit BLOCKED]:\n   • " + "\n   • ".join(safe_errors))
        return 1
    print(f"   ✅ pre-commit passed ({len(staged)} staged file(s) verified).")
    return 0


def run_pre_push(repo_root: Path) -> int:
    """Execute Silas Constitutional Verification Gate before git push."""
    print("🏛️  [Silas pre-push Gate] Verifying repository quality gates before push...")
    sweep_stray_backups(repo_root)
    verify_kb = repo_root / "scripts" / "verify_kb.py"
    if verify_kb.exists():
        return subprocess.run([sys.executable, str(verify_kb), "--scan-secrets", "--check-hygiene"], cwd=str(repo_root), check=False).returncode

    uv_bin, pyproject = shutil.which("uv"), repo_root / "pyproject.toml"
    if uv_bin and pyproject.exists() and (repo_root / "src").exists():
        cfg = pyproject.read_text(encoding="utf-8", errors="replace")
        targets = [t for t in ("src", "tests", "scripts") if (repo_root / t).exists()]
        sec_targets = [t for t in ("src", "scripts") if (repo_root / t).exists()]
        gates = [
            ("[tool.codespell]" in cfg, [uv_bin, "run", "codespell"]),
            ("[tool.black]" in cfg and bool(targets), [uv_bin, "run", "black", "--check", *targets]),
            ("[tool.ruff" in cfg and bool(targets), [uv_bin, "run", "ruff", "check", *targets]),
            ("[tool.bandit]" in cfg and bool(sec_targets), [uv_bin, "run", "bandit", "-c", "pyproject.toml", "-r", *sec_targets]),
            ("[tool.mypy]" in cfg, [uv_bin, "run", "mypy", *[t for t in ("src", "tests") if (repo_root / t).exists()]]),
            ((repo_root / "tests" / "unit").exists(), [uv_bin, "run", "pytest", "tests/unit", "-q", "--tb=short"]),
        ]
        for enabled, cmd in gates:
            if enabled and subprocess.run(cmd, cwd=str(repo_root), check=False).returncode != 0:
                return 1
    print("   ✅ Silas pre-push verification gate passed!")
    return 0


def install_git_hooks(repo_root: Path) -> int:
    """Configure git core.hooksPath to .githooks and ensure hook scripts are executable."""
    githooks = repo_root / ".githooks"
    if not githooks.exists() or _run_cmd(["git", "config", "core.hooksPath", ".githooks"], repo_root).returncode != 0:
        return 1
    for name in ("pre-commit", "pre-push"):
        if (githooks / name).exists():
            (githooks / name).chmod(0o755)
    print(f"✅ Configured git core.hooksPath -> .githooks in {repo_root}")
    return 0


def main() -> int:
    """CLI entrypoint for git hooks runner."""
    hook = sys.argv[1].lower() if len(sys.argv) > 1 else "pre-commit"
    root = resolve_repo_root()
    return run_pre_commit(root) if hook == "pre-commit" else (run_pre_push(root) if hook == "pre-push" else (install_git_hooks(root) if hook == "install" else 1))


if __name__ == "__main__":
    sys.exit(main())
