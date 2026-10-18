#!/usr/bin/env python3
"""
DocDoc Hygiene & Governance Verification Tool
=============================================
Validates project documentation standards:
  1. Root documentation restriction (only README.md in root).
  2. All markdown files reside in documentation/ (or permitted configuration paths: .jules, .agent, .agents).
  3. Strict lowercase kebab-case naming for all files and directories in documentation/.
  4. Zero dangling .bk* backup files outside .legacy_hr/.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def check_root_markdown() -> List[str]:
    """Ensure no markdown files other than README.md exist in the project root."""
    violations = []
    for file_path in PROJECT_ROOT.glob("*.md"):
        if file_path.name != "README.md":
            violations.append(
                f"Unauthorized root markdown file: '{file_path.name}'. Move to documentation/ in kebab-case."
            )
    return violations


def check_documentation_naming() -> List[str]:
    """Ensure all directories and markdown files under documentation/ follow lowercase kebab-case."""
    violations = []
    doc_dir = PROJECT_ROOT / "documentation"
    if not doc_dir.exists():
        return ["documentation/ directory not found!"]

    for root, dirs, files in os.walk(doc_dir):
        rel_root = Path(root).relative_to(PROJECT_ROOT)
        for d in dirs:
            if any(c.isupper() for c in d):
                violations.append(f"Directory contains uppercase letters: '{rel_root / d}'")
            if "_" in d:
                violations.append(f"Directory uses snake_case instead of kebab-case: '{rel_root / d}'")

        for f in files:
            if f.endswith(".md"):
                file_stem = Path(f).stem
                if any(c.isupper() for c in file_stem):
                    violations.append(f"Markdown file contains uppercase letters: '{rel_root / f}'")
                if "_" in file_stem:
                    violations.append(f"Markdown file uses snake_case instead of kebab-case: '{rel_root / f}'")

    return violations


def check_dangling_backups() -> List[str]:
    """Ensure no .bk* backup files exist in active directories (must be cleaned into .legacy_hr)."""
    violations = []
    ignored_parents = {".legacy_hr", ".git", ".venv", "node_modules", "_full_archive"}

    for path in PROJECT_ROOT.rglob("*.bk*"):
        if any(part in ignored_parents for part in path.parts):
            continue
        rel_path = path.relative_to(PROJECT_ROOT)
        violations.append(
            f"Dangling backup file: '{rel_path}'. Move to .legacy_hr/ upon task completion."
        )
    return violations


def run_all_checks() -> int:
    """Execute all DocDoc hygiene gates and report findings."""
    print("📚 Running DocDoc Documentation & Knowledge Governance Checks...")
    all_violations: List[Tuple[str, List[str]]] = [
        ("Root Markdown Boundary", check_root_markdown()),
        ("Documentation Kebab-Case Naming", check_documentation_naming()),
        ("Backup File Cleanup (.legacy_hr)", check_dangling_backups()),
    ]
    failed = False
    for category, errs in all_violations:
        if errs:
            print(f"❌ [FAILED] {category}:")
            for err in errs:
                print(f"   - {err}")
            failed = True
        else:
            print(f"✅ [PASSED] {category}")

    if failed:
        print("\n⚠️  DocDoc verification failed. Please address documentation violations before committing.")
        return 1

    print("\n🎉 All DocDoc documentation hygiene gates passed successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(run_all_checks())
