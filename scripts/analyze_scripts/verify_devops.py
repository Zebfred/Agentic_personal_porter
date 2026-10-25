#!/usr/bin/env python3
"""
DevOps Infrastructure & CI/CD Security Verification Tool
========================================================
Validates repository infrastructure and CI/CD security standards:
  1. Docker Compose syntax and configuration integrity.
  2. GitHub Actions SHA Pinning: All third-party actions must be pinned
     to an immutable 40-character commit SHA to protect against supply chain attacks.
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SHA_PATTERN = re.compile(r'^[0-9a-f]{40}$')


def check_github_actions_sha_pinning() -> List[str]:
    """Verify that all actions in .github/workflows/*.yml use 40-character immutable SHAs."""
    violations = []
    workflows_dir = PROJECT_ROOT / ".github" / "workflows"
    if not workflows_dir.exists():
        return ["No .github/workflows directory found."]

    uses_regex = re.compile(r'^\s*(?:-\s+)?uses:\s+([^\s#]+)(.*)$')

    for wf_file in workflows_dir.glob("*.y*ml"):
        with open(wf_file, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                match = uses_regex.match(line)
                if not match:
                    continue
                action_ref = match.group(1).strip().strip("'\"")
                # Skip local actions (e.g., ./...) or docker:// actions
                if action_ref.startswith("./") or action_ref.startswith("docker://"):
                    continue
                if "@" not in action_ref:
                    violations.append(
                        f"{wf_file.name}:{line_no} Action '{action_ref}' missing revision specifier."
                    )
                    continue

                action_name, ref = action_ref.split("@", 1)
                if not SHA_PATTERN.match(ref):
                    violations.append(
                        f"{wf_file.name}:{line_no} Action '{action_name}' is pinned to mutable ref '@{ref}'. "
                        f"Must be pinned to full 40-character commit SHA."
                    )
    return violations


def check_docker_compose_config() -> List[str]:
    """Validate docker-compose.yml files for syntax validity."""
    violations = []
    compose_file = PROJECT_ROOT / "docker-compose.yml"
    if not compose_file.exists():
        alt_files = list(PROJECT_ROOT.glob("docker-compose*.y*ml"))
        if not alt_files:
            return []
        compose_file = alt_files[0]

    try:
        res = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "config", "--quiet"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if res.returncode != 0:
            violations.append(f"docker-compose config validation error: {res.stderr.strip()}")
    except FileNotFoundError:
        # Docker not installed on runner; verify basic syntax/presence of required keys
        with open(compose_file, "r", encoding="utf-8") as f:
            content = f.read()
            if "services:" not in content:
                violations.append("docker-compose.yml missing 'services:' block.")
    except Exception as e:
        violations.append(f"Unexpected error validating docker-compose: {e}")

    return violations


def run_all_checks(strict: bool = False) -> int:
    """Execute all DevOps infrastructure and CI/CD security checks."""
    print("⚙️  Running DevOps CI/CD & Infrastructure Security Checks...")

    sha_violations = check_github_actions_sha_pinning()
    compose_violations = check_docker_compose_config()

    failed = False

    # Docker Compose Integrity
    if compose_violations:
        print("❌ [FAILED] Docker Compose Config Integrity:")
        for err in compose_violations:
            print(f"   - {err}")
        failed = True
    else:
        print("✅ [PASSED] Docker Compose Config Integrity")

    # GitHub Actions SHA Pinning
    if sha_violations:
        if strict:
            print(f"❌ [FAILED] GitHub Actions SHA Pinning ({len(sha_violations)} unpinned actions):")
            for err in sha_violations:
                print(f"   - {err}")
            failed = True
        else:
            print(f"⚠️  [NOTICE] GitHub Actions SHA Pinning ({len(sha_violations)} unpinned actions to pin):")
            for err in sha_violations[:5]:
                print(f"   - {err}")
            if len(sha_violations) > 5:
                print(f"   - ... and {len(sha_violations) - 5} more unpinned actions (run with --strict to enforce)")
    else:
        print("✅ [PASSED] GitHub Actions SHA Pinning (All 40-character SHAs verified)")

    if failed:
        print("\n⚠️  DevOps checks detected issues. Please review and secure infrastructure configurations.")
        return 1

    print("\n🎉 All DevOps infrastructure checks passed!")
    return 0


if __name__ == "__main__":
    is_strict = "--strict" in sys.argv
    sys.exit(run_all_checks(strict=is_strict))
