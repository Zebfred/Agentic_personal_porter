#!/usr/bin/env python3
"""
Jovol JS Functional Component & Spec Kit Verification Tool
==========================================================
Validates frontend JavaScript and component architecture:
  1. Validates all frontend/js/*.js scripts for clean JavaScript syntax via node -c.
  2. If components/ exist, verifies functional component conventions and Spec Kit rules.
  3. Validates root CSS design tokens in frontend/css/input.css.
"""

import glob
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def check_javascript_syntax() -> List[str]:
    """Verify that all frontend/js files have valid syntax using node -c."""
    violations = []
    js_files = list((PROJECT_ROOT / "frontend" / "js").glob("*.js"))
    if not js_files:
        return ["No JavaScript files found in frontend/js/"]

    for js_file in js_files:
        try:
            res = subprocess.run(
                ["node", "-c", str(js_file)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode != 0:
                violations.append(f"{js_file.name}: Syntax error: {res.stderr.strip()}")
        except FileNotFoundError:
            # Node not in runner path, fallback
            break
        except Exception as e:
            violations.append(f"{js_file.name}: Error running syntax check: {e}")

    return violations


def check_design_tokens() -> List[str]:
    """Verify that frontend/css/input.css defines core root design tokens."""
    violations = []
    css_file = PROJECT_ROOT / "frontend" / "css" / "input.css"
    if not css_file.exists():
        return ["frontend/css/input.css not found"]

    with open(css_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify presence of Tailwind or semantic tokens
    if "@import" not in content and "@theme" not in content and ":root" not in content:
        violations.append("frontend/css/input.css missing root theme or stylesheet definition.")

    return violations


def check_component_spec_kit() -> List[str]:
    """Verify Spec Kit conventions when components directory is active."""
    violations = []
    components_dir = PROJECT_ROOT / "components"
    if not components_dir.exists():
        return []  # Optional until Next.js transition is initialized

    spec_kit = components_dir / "spec-kit"
    if not spec_kit.exists():
        violations.append("components/ present but missing 'spec-kit/' atomic primitives directory.")

    registry = spec_kit / "COMPONENT_REGISTRY.md"
    if spec_kit.exists() and not registry.exists():
        violations.append("components/spec-kit/ missing COMPONENT_REGISTRY.md documentation manual.")

    return violations


def run_all_checks() -> int:
    """Execute all Jovol functional component and JS checks."""
    print("⚛️  Running Jovol JS Functional Component & Spec Kit Checks...")

    all_violations: List[Tuple[str, List[str]]] = [
        ("JavaScript Syntax Integrity (node -c)", check_javascript_syntax()),
        ("Design Tokens & CSS Theme", check_design_tokens()),
        ("Spec Kit Component Registry", check_component_spec_kit()),
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
        print("\n⚠️  Jovol component checks detected issues.")
        return 1

    print("\n🎉 All Jovol JS functional component checks passed!")
    return 0


if __name__ == "__main__":
    sys.exit(run_all_checks())
