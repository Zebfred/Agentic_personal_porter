#!/usr/bin/env python3
"""DocDoc Hygiene, Skill Security & Constitution Leak Verification Tool (< 200L, < 60L fns)."""

# fmt: off
from __future__ import annotations
import os, re, subprocess, sys  # noqa: E401  # nosec B404
from pathlib import Path
from typing import List, Tuple

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ABSOLUTE_USER_PATH_RE = re.compile(r"(?i)(file:///(?:home|Users)/|/(?:home|Users)/[a-zA-Z0-9._-]+/|[a-z]:\\users\\[a-z0-9._-]+)")
SUPPLY_CHAIN_PATTERNS = [
    (r"(?i)\b(?:npx|npm\s+exec|uvx)\b[^\r\n]*?@latest\b", "Mutable @latest package execution"),
    (r"(?i)\b(?:curl|wget|iwr|Invoke-WebRequest)\b[^\r\n]*?\|\s*(?:sh|bash|zsh|pwsh|powershell|iex)\b", "Remote pipe-to-shell execution"),
    (r"(?i)\b(?:ignore\s+(?:all\s+)?(?:previous|prior|system)\s+instructions|disregard\s+(?:all\s+)?(?:previous|system)\s+instructions)\b", "Prompt-injection override pattern"),
]
CONSTITUTION_LEAK_RE = re.compile(r"(?i)(Nexus_Constitution\.md|LEVEL-0\s+COMPANY\s+CONSTITUTION|nexus-ds-ml-consulting|Nexus\s+LLC)")


def check_root_markdown(repo_root: Path = PROJECT_ROOT) -> List[str]:
    """Ensure no markdown files other than README.md and AGENTS.md exist in the project root."""
    allowed_root = {"README.md", "AGENTS.md"}
    return [
        f"Unauthorized root markdown file: '{p.name}'. Move to documentation/ in kebab-case."
        for p in repo_root.glob("*.md")
        if p.name not in allowed_root
    ]


def check_documentation_naming(repo_root: Path = PROJECT_ROOT) -> List[str]:
    """Ensure all directories and markdown files under documentation/ follow lowercase kebab-case."""
    violations: List[str] = []
    doc_dir = repo_root / "documentation"
    if not doc_dir.exists():
        return ["documentation/ directory not found!"]
    for root, dirs, files in os.walk(doc_dir):
        dirs[:] = [d for d in dirs if d != ".organization_discrete"]
        rel_root = Path(root).relative_to(repo_root)
        for d in dirs:
            if any(c.isupper() for c in d) or "_" in d:
                violations.append(f"Non-kebab-case directory: '{rel_root / d}'")
        for f in files:
            if f.endswith(".md"):
                stem = Path(f).stem
                if any(c.isupper() for c in stem) or "_" in stem:
                    violations.append(f"Non-kebab-case markdown file: '{rel_root / f}'")
    return violations


def check_dangling_backups(repo_root: Path = PROJECT_ROOT) -> List[str]:
    """Ensure no .bk* backup files exist in active directories (must be archived in .legacy_hr)."""
    ignored = {".legacy_hr", ".git", ".venv", "node_modules", "_full_archive"}
    return [
        f"Dangling backup file: '{p.relative_to(repo_root)}'. Move to .legacy_hr/."
        for p in repo_root.rglob("*.bk*")
        if not any(part in ignored for part in p.parts)
    ]


def check_no_absolute_paths(repo_root: Path = PROJECT_ROOT) -> List[str]:
    """Ensure no hardcoded workstation-specific paths exist in active tracked sources."""
    violations: List[str] = []
    targets = ["README.md", "documentation", "specs", ".agents", ".jules", "src", "tests"]
    exts = {".md", ".py", ".json", ".yml", ".yaml", ".js", ".html", ".css"}
    for t_name in targets:
        target = repo_root / t_name
        paths = [target] if target.is_file() else (list(target.rglob("*")) if target.is_dir() else [])
        for p in paths:
            if not p.is_file() or p.suffix not in exts or "__pycache__" in p.parts or ".organization_discrete" in p.parts:
                continue
            for lineno, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if ABSOLUTE_USER_PATH_RE.search(line):
                    violations.append(f"Hardcoded user path in '{p.relative_to(repo_root)}:{lineno}'.")
    return violations


def check_skill_hygiene(repo_root: Path = PROJECT_ROOT) -> List[str]:
    """Enforce SKILL001-SKILL006 progressive disclosure & supply-chain security on .agents/."""
    errors: List[str] = []
    agents_dir = repo_root / ".agents"
    if not agents_dir.exists():
        return errors
    for cfg in sorted(agents_dir.rglob("*.json")):
        raw_cfg, rel_cfg = cfg.read_text(encoding="utf-8", errors="replace"), cfg.relative_to(repo_root).as_posix()
        errors.extend(f"[SKILL006 supply-chain] {rel_cfg}: {lbl}." for pat, lbl in SUPPLY_CHAIN_PATTERNS if re.search(pat, raw_cfg))
    for skill_md in sorted((agents_dir / "skills").rglob("SKILL.md")) if (agents_dir / "skills").exists() else []:
        rel, raw = skill_md.relative_to(repo_root).as_posix(), skill_md.read_text(encoding="utf-8", errors="replace")
        if len(raw.splitlines()) >= 500:
            errors.append(f"[SKILL003 body-limit] {rel}: {len(raw.splitlines())} lines (>= 500 max).")
        fm_match = re.match(r"^---\r?\n(.*?)\r?\n---", raw, flags=re.DOTALL)
        if not fm_match:
            errors.append(f"[SKILL001 frontmatter] {rel}: Missing YAML frontmatter ('---' block).")
            continue
        fm = fm_match.group(1)
        desc_m = re.search(r"(?m)^description:\s*(.+)$", fm)
        if not re.search(r"(?m)^name:\s*(.+)$", fm) or not desc_m:
            errors.append(f"[SKILL001 frontmatter] {rel}: Requires both 'name:' and 'description:'.")
        elif not (5 <= len(desc_m.group(1).strip().split()) <= 100):
            errors.append(f"[SKILL002 description-budget] {rel}: description must be 5..100 words.")
        if re.search(r'(?i)tools\s*:\s*\[\s*["\']\*["\']\s*\]', fm):
            errors.append(f"[SKILL005 unscoped-tools] {rel}: Blanket tools: ['*'] is forbidden.")
        if ABSOLUTE_USER_PATH_RE.search(raw):
            errors.append(f"[SKILL004 hardcoded-path] {rel}: Contains machine-specific user path.")
        errors.extend(f"[SKILL006 supply-chain] {rel}: {lbl}." for pat, lbl in SUPPLY_CHAIN_PATTERNS if re.search(pat, raw))
    return errors


def check_constitution_and_discrete_leaks(repo_root: Path = PROJECT_ROOT) -> List[str]:
    """Ensure .organization_discrete/ is gitignored and no Level-0 Constitution markers leak."""
    errors: List[str] = []
    gitignore = repo_root / ".gitignore"
    if not gitignore.exists() or ".organization_discrete" not in gitignore.read_text(encoding="utf-8", errors="ignore"):
        errors.append("Missing 'documentation/.organization_discrete/' entry in .gitignore.")
    res = subprocess.run(["git", "ls-files"], cwd=str(repo_root), capture_output=True, text=True, check=False)  # nosec B603 B607
    tracked = [ln.strip() for ln in res.stdout.splitlines() if ln.strip()] if res.returncode == 0 else []
    skip_files = {"verify_doc_hygiene.py", "git_hooks_runner.py", "secret-scan.yml"}
    for rel_path in tracked:
        norm = rel_path.replace("\\", "/")
        if norm != ".legacy_hr/.gitignore" and norm.startswith((".auth/", ".legacy_hr/", ".logs/", "documentation/.organization_discrete/", ".organization_discrete/")):
            errors.append(f"Restricted file tracked by Git: '{norm}'.")
        p = repo_root / rel_path
        if p.is_file() and p.name not in skip_files and not norm.startswith("tests/") and p.suffix in {".md", ".py", ".json", ".yml", ".yaml", ".html"}:
            if CONSTITUTION_LEAK_RE.search(p.read_text(encoding="utf-8", errors="ignore")):
                errors.append(f"Level-0 Company Constitution marker leaked in tracked file: '{norm}'.")
    return errors


def run_all_checks(repo_root: Path = PROJECT_ROOT) -> int:
    """Execute all DocDoc, Skill, and Constitution Leak gates."""
    print("📚 Running DocDoc Documentation, Skill & Constitution Governance Checks...")
    checks: List[Tuple[str, List[str]]] = [
        ("Root Markdown Boundary", check_root_markdown(repo_root)),
        ("Documentation Kebab-Case Naming", check_documentation_naming(repo_root)),
        ("Relative Path Portability (No Hardcoded User Paths)", check_no_absolute_paths(repo_root)),
        ("Backup File Cleanup (.legacy_hr)", check_dangling_backups(repo_root)),
        ("Agent Skill Security & Progressive Disclosure (SKILL001-006)", check_skill_hygiene(repo_root)),
        ("Discrete Spec & Company Constitution Leak Gate", check_constitution_and_discrete_leaks(repo_root)),
    ]
    failed = False
    for category, errs in checks:
        if errs:
            print(f"❌ [FAILED] {category}:\n   - " + "\n   - ".join(errs))
            failed = True
        else:
            print(f"✅ [PASSED] {category}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run_all_checks())
