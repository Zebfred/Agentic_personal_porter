#!/usr/bin/env python3
"""Standardized Git Hooks Runner (`pre-commit` & `pre-push` gates, < 200L script, < 60L functions)."""

# fmt: off
from __future__ import annotations
import ast, os, re, shutil, subprocess, sys  # noqa: E401  # nosec B404
from pathlib import Path
from typing import List, Sequence
from agent_lifecycle_hooks import ALLOWED_PLACEHOLDERS, GUARDRAIL_PATTERNS, sweep_stray_backups

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"): _stream.reconfigure(encoding="utf-8", errors="replace")

MAX_SCRIPT_LINES, MAX_FUNCTION_LINES, MAX_PR_FILES = 200, 60, 35
LEGACY_EXEMPT_SCRIPTS = {"trace_lineage.py", "seed_calendar.py", "test_calendar_pull.py"}
KV_REDACT_RE = re.compile(r"(?i)\b(pass[w]ord|pass[w]d|tok[e]n|secr[e]t|api[_-]?k[e]y|access[_-]?k[e]y)\b\s*[:=]\s*([^\s,;]+)")
LEAK_RE = re.compile(r"(?i)(Nexus_Constitution\.md|LEVEL-0\s+COMPANY\s+CONSTITUTION|nexus-ds-ml-consulting|Nexus\s+LLC)")


def _sanitize_error_for_logging(message: str) -> str:
    """Redact credential-like fragments before writing hook diagnostics to stdout."""
    redacted = message
    for pattern, _ in GUARDRAIL_PATTERNS:
        try: redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)
        except re.error: continue
    return KV_REDACT_RE.sub(r"\1=[REDACTED]", redacted)


def resolve_repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parents[1]


def _run_cmd(args: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command and capture UTF-8 output."""
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)  # nosec B603


def check_branch_and_pr_size(repo_root: Path, staged_count: int) -> List[str]:
    """Enforce 3-Tier Git Flow (no direct commits on main/master) and <= 35-file PR limit."""
    errors: List[str] = []
    b_res = _run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    branch = b_res.stdout.strip() if b_res.returncode == 0 else ""
    if branch in {"main", "master"} and os.environ.get("ALLOW_MAIN_COMMIT") != "1":
        errors.append(f"Direct commits to '{branch}' blocked (3-Tier Git Flow). Use a working branch or topic worktree.")
    d_res = _run_cmd(["git", "diff", "--name-only", "origin/main...HEAD"], repo_root)
    changed = {ln.strip() for ln in d_res.stdout.splitlines() if ln.strip()} if d_res.returncode == 0 else set()
    total = max(staged_count, len(changed))
    if total > MAX_PR_FILES and os.environ.get("ALLOW_LARGE_PR") != "1":
        print(f"   ⚠️  [35-File Stacked PR Rule] {total} files modified (> {MAX_PR_FILES}). Split into a PR Stack.")
        if staged_count > MAX_PR_FILES: errors.append(f"Staged commit modifies {staged_count} files (max <= {MAX_PR_FILES}).")
    return errors


def scan_staged_diff_guardrails(repo_root: Path) -> List[str]:
    """Scan added lines in `git diff --cached` against guardrail and constitution leak patterns."""
    res = _run_cmd(["git", "diff", "--cached", "-U0"], repo_root)
    violations, current = [], "unknown"
    skip = {"agent_lifecycle_hooks.py", "git_hooks_runner.py", "verify_kb.py", "verify_doc_hygiene.py", "build_context_pack.py", "secret-scan.yml"}
    for line in (res.stdout.splitlines() if res.returncode == 0 else []):
        if line.startswith("+++ b/"): current = line[6:].strip()
        elif Path(current).name not in skip and line.startswith("+") and not line.startswith("+++"):
            added = line[1:]
            if not any(m in added for m in ALLOWED_PLACEHOLDERS):
                violations.extend(f"[{rule_id}] triggered in staged file '{current}'" for pat, rule_id in GUARDRAIL_PATTERNS if re.search(pat, added))
                if not current.startswith("tests/") and LEAK_RE.search(added):
                    violations.append(f"[CONSTITUTION_LEAK] Restricted company/constitution marker in staged file '{current}'")
    return violations


def check_python_modularity(repo_root: Path, staged_py: Sequence[str]) -> List[str]:
    """Verify generated scripts are < 200 lines and functions are < 60 lines."""
    errors: List[str] = []
    for rel_path in staged_py:
        py_file, norm = repo_root / rel_path, rel_path.replace("\\", "/")
        if not py_file.exists() or not norm.startswith("scripts/") or py_file.name in LEGACY_EXEMPT_SCRIPTS: continue
        source = py_file.read_text(encoding="utf-8", errors="replace")
        if len(source.splitlines()) >= MAX_SCRIPT_LINES: errors.append(f"[Script Length >= {MAX_SCRIPT_LINES}L] '{norm}' has {len(source.splitlines())} lines.")
        try: tree = ast.parse(source, filename=rel_path)
        except SyntaxError as exc: errors.append(f"[SyntaxError] '{norm}': {exc}")
        else:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.end_lineno and (node.end_lineno - node.lineno + 1) >= MAX_FUNCTION_LINES:
                    errors.append(f"[Function Length >= {MAX_FUNCTION_LINES}L] '{norm}:{node.lineno}' '{node.name}' is {node.end_lineno - node.lineno + 1}L.")
    return errors


def _run_staged_linters(repo_root: Path, staged: Sequence[str], staged_py: Sequence[str]) -> List[str]:
    """Execute codespell, black, ruff, bandit, vulture, and deadcode on staged files when configured."""
    pyproject, uv_bin = repo_root / "pyproject.toml", shutil.which("uv")
    if not pyproject.exists() or not uv_bin:
        return []
    cfg = pyproject.read_text(encoding="utf-8", errors="replace")
    existing = [p for p in staged if (repo_root / p).is_file() and Path(p).name != "uv.lock" and not p.endswith(".lock") and not p.startswith("agentic-private-brain")]
    non_test_py = [p for p in staged_py if not p.replace("\\", "/").startswith(("tests/", "agentic-private-brain/"))]
    v_bin, d_bin = shutil.which("vulture"), shutil.which("deadcode")
    py_roots = [t for t in ("src", "tests", "scripts") if (repo_root / t).exists()]
    checks = [
        ("Codespell", bool(existing) and "[tool.codespell]" in cfg, [uv_bin, "run", "--no-sync", "codespell", *existing]),
        ("Black", bool(staged_py) and "[tool.black]" in cfg, [uv_bin, "run", "--no-sync", "black", "--check", "--diff", *staged_py]),
        ("Ruff", bool(staged_py) and "[tool.ruff" in cfg, [uv_bin, "run", "--no-sync", "ruff", "check", *staged_py]),
        ("Bandit", bool(non_test_py) and "[tool.bandit]" in cfg, [uv_bin, "run", "--no-sync", "bandit", "-c", "pyproject.toml", "-q", *non_test_py]),
        ("Vulture", bool(non_test_py) and "[tool.vulture]" in cfg and bool(v_bin), [v_bin or "vulture", *non_test_py, "--min-confidence", "80"]),
    ]
    errs = [f"{lbl} failed:\n{r.stdout or r.stderr}" for lbl, on, cmd in checks if on and (r := _run_cmd(cmd, repo_root)).returncode != 0]
    if non_test_py and "[tool.deadcode]" in cfg and d_bin and (dc := _run_cmd([d_bin, *py_roots, "--only", *non_test_py], repo_root)).stdout.strip():
        errs.append(f"Deadcode failed:\n{dc.stdout}")
    return errs


def run_pre_commit(repo_root: Path) -> int:
    """Execute sub-second pre-commit checks on staged files."""
    print("🛡️  [Git Hook] Running pre-commit checks...")
    if sweep_stray_backups(repo_root) > 0:
        print("   📦 Auto-archived stray .bk file(s) into .legacy_hr/DDMMYYYY/")
    res = _run_cmd(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"], repo_root)
    staged = [line.strip() for line in res.stdout.splitlines() if line.strip()] if res.returncode == 0 else []
    if not staged:
        print("   ✅ No staged files to check.")
        return 0
    errors, staged_py, staged_js, touches_agents = check_branch_and_pr_size(repo_root, len(staged)), [], [], False
    for rel_path in staged:
        norm, parts = rel_path.replace("\\", "/"), rel_path.replace("\\", "/").split("/")
        fname, touches_agents = parts[-1], touches_agents or parts[0] == ".agents"
        if parts[0] in {".auth", ".legacy_hr", ".logs"} or ".organization_discrete" in parts or ".bk" in fname or fname.endswith(".pyc"):
            errors.append(f"Forbidden path or discrete/backup artifact staged: '{norm}'.")
        if parts[0] == "data" and norm != "data/.gitkeep" and ".example." not in fname:
            errors.append(f"Forbidden domain data file staged in data/: '{norm}'.")
        if len(parts) == 1 and fname.lower().endswith(".md") and fname not in {"README.md", "AGENTS.md"}:
            errors.append(f"Unauthorized root Markdown staged: '{fname}'.")
        if parts[0].lower() == "documentation" and fname.lower().endswith(".md") and (any(c.isupper() for c in Path(fname).stem) or "_" in Path(fname).stem):
            errors.append(f"Non-kebab-case Markdown file in documentation/: '{norm}'")
        if (repo_root / rel_path).is_file():
            (staged_py if fname.endswith(".py") else staged_js if fname.endswith(".js") else []).append(rel_path)
    doc_hygiene = repo_root / "scripts" / "analyze_scripts" / "verify_doc_hygiene.py"
    if touches_agents and doc_hygiene.exists():
        sys.path.insert(0, str(doc_hygiene.parent))
        from verify_doc_hygiene import check_skill_hygiene
        errors.extend(check_skill_hygiene(repo_root))
    errors.extend(scan_staged_diff_guardrails(repo_root) + check_python_modularity(repo_root, staged_py) + _run_staged_linters(repo_root, staged, staged_py))
    if node_bin := (shutil.which("node") or shutil.which("node.exe")):
        errors.extend(f"JavaScript syntax check (node -c) failed for '{js}'." for js in staged_js if _run_cmd([node_bin, "-c", js], repo_root).returncode != 0)
    if errors:
        print("\n❌ [pre-commit BLOCKED]:\n   • " + "\n   • ".join(_sanitize_error_for_logging(e) for e in errors))
        return 1
    print(f"   ✅ pre-commit passed ({len(staged)} staged file(s) verified).")
    return 0


def run_pre_push(repo_root: Path) -> int:
    """Execute Silas Constitutional Verification Gate before git push."""
    print("🏛️  [Silas pre-push Gate] Verifying repository quality gates before push...")
    sweep_stray_backups(repo_root)
    if check_branch_and_pr_size(repo_root, 0):
        print("❌ [Silas pre-push BLOCKED] Cannot push directly from main/master without ALLOW_MAIN_COMMIT=1.")
        return 1
    uv_bin, pyproject = shutil.which("uv"), repo_root / "pyproject.toml"
    if uv_bin and pyproject.exists() and (repo_root / "src").exists():
        cfg = pyproject.read_text(encoding="utf-8", errors="replace")
        targets = [t for t in ("src", "tests", "scripts") if (repo_root / t).exists()]
        branch_py = [p for p in _run_cmd(["git", "diff", "--name-only", "--diff-filter=ACMR", "origin/main...HEAD"], repo_root).stdout.splitlines() if p.endswith(".py") and (repo_root / p).is_file()] or targets
        sec_targets = [t for t in ("src", "scripts") if (repo_root / t).exists()]
        env = {**os.environ, "PROJECT_ID": os.environ.get("PROJECT_ID", "test-project"), "DISABLE_CLOUD_LOGGING": "true"}
        gates = [
            ("[tool.codespell]" in cfg, [uv_bin, "run", "--no-sync", "codespell"]),
            ("[tool.black]" in cfg and bool(branch_py), [uv_bin, "run", "--no-sync", "black", "--check", *branch_py]),
            ("[tool.ruff" in cfg and bool(targets), [uv_bin, "run", "--no-sync", "ruff", "check", *targets]),
            ("[tool.bandit]" in cfg and bool(sec_targets), [uv_bin, "run", "--no-sync", "bandit", "-c", "pyproject.toml", "-r", *sec_targets]),
            ("[tool.mypy]" in cfg, [uv_bin, "run", "--no-sync", "mypy", "src"]),
            ((repo_root / "tests" / "unit").exists(), [uv_bin, "run", "--no-sync", "pytest", "tests/unit", "-q", "--tb=short"]),
        ]
        for enabled, cmd in gates:
            if enabled and subprocess.run(cmd, cwd=str(repo_root), env=env, check=False).returncode != 0:  # nosec B603
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
    hook, root = (sys.argv[1].lower() if len(sys.argv) > 1 else "pre-commit"), resolve_repo_root()
    return run_pre_commit(root) if hook == "pre-commit" else (run_pre_push(root) if hook == "pre-push" else (install_git_hooks(root) if hook == "install" else 1))


if __name__ == "__main__":
    sys.exit(main())
