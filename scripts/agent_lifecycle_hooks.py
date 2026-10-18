#!/usr/bin/env python3
"""Standardized Antigravity CLI & IDE Lifecycle Hooks (agent_lifecycle_hooks.py).

Enforces Nexus LLC Constitutional guardrails at runtime across PreToolUse,
PostToolUse, and Stop lifecycle events:
1. PreToolUse:
   - Blocks plaintext secrets/tokens from being written into tracked files (Sentinel 🛡️).
   - Enforces lowercase kebab-case in documentation/ and root README.md/AGENTS.md boundary (DocDoc 📚).
   - Automatically snapshots a timestamped .bk backup into .legacy_hr/hook_backups/ before modifying an existing file.
   - Prompts for confirmation ('ask') before high-risk destructive shell commands.
2. PostToolUse & Stop:
   - Automatically sweeps any lingering *.bk* backup files into .legacy_hr/hook_backups/ so active directories stay clean.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SECRET_PATTERNS = [
    (r'AIza[0-9A-Za-z\-_]{35}', "Google API Key"),
    (r'GOCSPX-[0-9A-Za-z\-_]{20,}', "Google OAuth Client Secret"),
    (r'gsk_[0-9A-Za-z]{20,}', "Groq API Key"),
    (r'gh[po]_[0-9A-Za-z]{30,}', "GitHub Personal/OAuth Token"),
    (r'AQ\.Ab8RN6[0-9A-Za-z\-_]{20,}', "Google Cloud Token"),
    (r'-----BEGIN [A-Z ]*PRIVATE KEY-----', "Private Key Block"),
    (r'(?i)mongodb\+srv:\/\/[^:\s]+:[^@\s]+@', "MongoDB URI with Embedded Credentials"),
]

DESTRUCTIVE_CMD_PATTERNS = [
    (r'(?i)\bdrop\s+(table|database|schema)\b', "SQL DROP statement"),
    (r'(?i)\btruncate\s+table\b', "SQL TRUNCATE statement"),
    (r'(?i)\bgcloud\s+projects\s+delete\b', "GCP project deletion"),
    (r'(?i)\bgsutil\s+rm\s+-[rf]*r', "Recursive GCS bucket deletion"),
    (r'(?i)\bgit\s+push\b(?=.*--force\b)(?!.*--force-with-lease).*\b(main|master)\b', "Unprotected force-push to main/master"),
]

ABSOLUTE_PATH_PATTERNS = [
    (r'(?i)(?<![A-Za-z0-9_])[A-Za-z]:[\\/](?:Users|home|Program Files|Windows|nvm4w)[\\/][^\s"\'\)\]`>]+', "Hardcoded Windows User/System Path"),
    (r'(?i)(?<![A-Za-z0-9_])/(?:Users|home|mnt/[a-z])/[A-Za-z0-9._\-]+/[^\s"\'\)\]`>]+', "Hardcoded Unix/WSL Home Path"),
    (r'(?i)file:///[A-Za-z]:/', "Hardcoded Windows file:/// URI in repository file"),
    (r'(?i)file:///(?:home|Users|mnt)/', "Hardcoded Unix/WSL file:/// URI in repository file"),
]

SAFE_PLACEHOLDERS = ("${", "NORDPASS", "[PASSWORD]", "<db_password>", "<PASSWORD>", "YOUR_API_KEY", "example")


def resolve_repo_root() -> Path:
    """Resolve the repository root from the script location (<repo>/scripts/agent_lifecycle_hooks.py)."""
    return Path(__file__).resolve().parents[1]


def sweep_stray_backups(repo_root: Path) -> int:
    """Move any lingering *.bk* files outside .legacy_hr/ into .legacy_hr/hook_backups/."""
    if not repo_root.exists():
        return 0

    backup_dir = repo_root / ".legacy_hr" / "hook_backups"
    ignored_dirs = {".git", ".legacy_hr", ".venv", "venv", "node_modules", "__pycache__"}
    moved_count = 0

    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for file in files:
            if file.endswith(".bk") or ".bk." in file or re.search(r"\.bk\d*$", file):
                src_path = Path(root) / file
                backup_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                dst_path = backup_dir / f"{file}.{timestamp}"
                try:
                    shutil.move(str(src_path), str(dst_path))
                    moved_count += 1
                except OSError:
                    pass
    return moved_count


def snapshot_before_edit(target_file: Path, repo_root: Path) -> Optional[Path]:
    """Create a timestamped .bk backup directly inside .legacy_hr/hook_backups/ before modifying an existing file."""
    if not target_file.exists() or not target_file.is_file():
        return None

    try:
        rel = target_file.resolve().relative_to(repo_root.resolve())
        if rel.parts and rel.parts[0] == ".legacy_hr":
            return None
    except ValueError:
        # Target file is outside this repository (e.g., scratch/artifact file)
        return None

    backup_dir = repo_root / ".legacy_hr" / "hook_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_rel = "__".join(rel.parts)
    backup_path = backup_dir / f"{safe_rel}.{timestamp}.bk"
    try:
        shutil.copy2(target_file, backup_path)
        return backup_path
    except OSError:
        return None


def validate_file_governance(target_file: Path, content: str, repo_root: Path) -> Optional[str]:
    """Return a denial reason if the file write violates secret isolation or documentation kebab-case rules."""
    # Skip governance checks on hook/scanner scripts that define regex patterns
    if target_file.name in {"agent_lifecycle_hooks.py", "git_hooks_runner.py", "verify_kb.py", "build_context_pack.py"}:
        return None

    # 1. Scan new content for plaintext secrets and hardcoded OS absolute paths
    for line in content.splitlines():
        if any(marker in line for marker in SAFE_PLACEHOLDERS):
            continue
        for pattern, label in SECRET_PATTERNS:
            if re.search(pattern, line):
                return (
                    f"🛡️ Sentinel Hook Blocked Edit: Detected potential plaintext {label} in '{target_file.name}'. "
                    f"Store credentials in .auth/.env or NordPass and use ${{ENV_VAR}} placeholders."
                )
        for pattern, label in ABSOLUTE_PATH_PATTERNS:
            if re.search(pattern, line):
                return (
                    f"🛡️ Sentinel Hook Blocked Edit: Detected {label} in '{target_file.name}'. "
                    f"Use project-root relative paths or Path(__file__).resolve() instead of OS absolute paths."
                )

    # 2. Check repo-relative path rules if target_file is inside repo_root
    try:
        rel = target_file.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None

    parts = rel.parts
    if not parts:
        return None

    # Root markdown check: only README.md and AGENTS.md permitted at repo root
    if len(parts) == 1 and parts[0].lower().endswith(".md"):
        if parts[0] not in {"README.md", "AGENTS.md"}:
            return (
                f"📚 DocDoc Hook Blocked Edit: Unauthorized root markdown file '{parts[0]}'. "
                f"Only README.md and AGENTS.md are permitted at the repository root; place docs in documentation/ using kebab-case."
            )

    # documentation/ directory check: enforce lowercase kebab-case
    if parts[0].lower() == "documentation":
        for sub_part in parts[1:-1]:
            if any(c.isupper() for c in sub_part) or "_" in sub_part:
                return (
                    f"📚 DocDoc Hook Blocked Edit: Directory '{sub_part}' under documentation/ must use lowercase kebab-case."
                )
        filename = parts[-1]
        if filename.lower().endswith(".md"):
            stem = Path(filename).stem
            if any(c.isupper() for c in stem) or "_" in stem:
                return (
                    f"📚 DocDoc Hook Blocked Edit: Markdown file '{filename}' under documentation/ must use lowercase kebab-case "
                    f"(e.g., '{stem.lower().replace('_', '-')}.md')."
                )

    return None


def handle_pre_tool_use(payload: Dict[str, Any], repo_root: Path) -> Dict[str, Any]:
    """Evaluate PreToolUse hook payload and return allow, ask, or deny decision."""
    tool_call = payload.get("toolCall") or {}
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args") or {}

    if tool_name == "run_command":
        cmd_line = str(args.get("CommandLine", ""))
        for pattern, label in DESTRUCTIVE_CMD_PATTERNS:
            if re.search(pattern, cmd_line):
                return {
                    "decision": "ask",
                    "reason": f"⚠️ Nexus Safety Hook: High-risk command detected ({label}). Please confirm execution.",
                }
        return {"decision": "allow"}

    if tool_name in {"write_to_file", "replace_file_content"}:
        raw_target = args.get("TargetFile")
        if not raw_target:
            return {"decision": "allow"}
        target_path = Path(str(raw_target))
        content = str(args.get("CodeContent") or args.get("ReplacementContent") or "")

        violation = validate_file_governance(target_path, content, repo_root)
        if violation:
            return {"decision": "deny", "reason": violation}

        # Automatically snapshot .bk backup into .legacy_hr/hook_backups/ before modifying existing file
        snapshot_before_edit(target_path, repo_root)
        return {"decision": "allow"}

    return {"decision": "allow"}


def main() -> int:
    """Entrypoint for Antigravity lifecycle hooks."""
    event = sys.argv[1].lower() if len(sys.argv) > 1 else "pre-tool-use"
    repo_root = resolve_repo_root()

    raw_stdin = sys.stdin.read().strip()
    payload: Dict[str, Any] = {}
    if raw_stdin:
        try:
            payload = json.loads(raw_stdin)
        except json.JSONDecodeError:
            payload = {}

    if event == "pre-tool-use":
        result = handle_pre_tool_use(payload, repo_root)
        print(json.dumps(result))
        return 0

    if event == "post-tool-use":
        sweep_stray_backups(repo_root)
        print(json.dumps({}))
        return 0

    if event == "stop":
        sweep_stray_backups(repo_root)
        print(json.dumps({"decision": "allow"}))
        return 0

    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
