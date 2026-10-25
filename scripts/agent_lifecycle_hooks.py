#!/usr/bin/env python3
"""Standardized Antigravity CLI & IDE Lifecycle Hooks (agent_lifecycle_hooks.py).

Enforces Nexus LLC guardrails at runtime across PreToolUse, PostToolUse, and Stop
events while keeping generated scripts < 200 lines and functions < 60 lines.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SECRET_PATTERNS = [
    (r"AIza[0-9A-Za-z\-_]{35}", "Google API Key"),
    (r"GOCSPX-[0-9A-Za-z\-_]{20,}", "Google OAuth Client Secret"),
    (r"gsk_[0-9A-Za-z]{20,}", "Groq API Key"),
    (r"gh[po]_[0-9A-Za-z]{30,}", "GitHub Personal/OAuth Token"),
    (r"AQ\.Ab8RN6[0-9A-Za-z\-_]{20,}", "Google Cloud Token"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "Private Key Block"),
    (r"(?i)mongodb\+srv:\/\/[^:\s]+:[^@\s]+@", "MongoDB URI with Embedded Credentials"),
]

DESTRUCTIVE_CMD_PATTERNS = [
    (r"(?i)\bdrop\s+(table|database|schema)\b", "SQL DROP statement"),
    (r"(?i)\btruncate\s+table\b", "SQL TRUNCATE statement"),
    (r"(?i)\bgcloud\s+projects\s+delete\b", "GCP project deletion"),
    (r"(?i)\bgsutil\s+rm\s+-[rf]*r", "Recursive GCS bucket deletion"),
    (r"(?i)\bgit\s+push\b(?=.*--force\b)(?!.*--force-with-lease).*\b(main|master)\b", "Force-push to main/master"),
]

SAFE_PLACEHOLDERS = ("${", "NORDPASS", "[PASSWORD]", "<db_password>", "<PASSWORD>", "YOUR_API_KEY", "example")
SKIP_GOVERNANCE_FILES = {"agent_lifecycle_hooks.py", "git_hooks_runner.py", "verify_kb.py", "build_context_pack.py"}


def resolve_repo_root() -> Path:
    """Resolve the repository root from `<repo>/scripts/agent_lifecycle_hooks.py`."""
    return Path(__file__).resolve().parents[1]


def sweep_stray_backups(repo_root: Path) -> int:
    """Move any lingering `*.bk*` files outside `.legacy_hr/` into `.legacy_hr/DDMMYYYY/`."""
    try:
        from log_run import sweep_stray_backups_to_daily

        return sweep_stray_backups_to_daily(repo_root)
    except (ImportError, OSError):
        if not repo_root.exists():
            return 0
        now = datetime.datetime.now()
        backup_dir = repo_root / ".legacy_hr" / now.strftime("%d%m%Y")
        ignored = {".git", ".legacy_hr", ".logs", ".venv", "venv", "node_modules", "__pycache__"}
        moved = 0
        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [d for d in dirs if d not in ignored]
            for f in files:
                if f.endswith(".bk") or ".bk." in f or re.search(r"\.bk\d*$", f):
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(Path(root) / f), str(backup_dir / f"{f}.{now.strftime('%H%M%S')}"))
                    moved += 1
        return moved


def snapshot_before_edit(target_file: Path, repo_root: Path) -> Path | None:
    """Create a timestamped `.bk` backup inside `.legacy_hr/DDMMYYYY/` before modifying an existing file."""
    try:
        from log_run import archive_backup_file

        return archive_backup_file(target_file, repo_root, copy_only=True)
    except (ImportError, OSError):
        if not target_file.exists() or not target_file.is_file():
            return None
        now = datetime.datetime.now()
        backup_dir = repo_root / ".legacy_hr" / now.strftime("%d%m%Y")
        backup_dir.mkdir(parents=True, exist_ok=True)
        dst = backup_dir / f"{target_file.name}.{now.strftime('%H%M%S')}.bk"
        shutil.copy2(target_file, dst)
        return dst


def validate_file_governance(target_file: Path, content: str, repo_root: Path) -> str | None:
    """Return a denial reason if the file write violates secret isolation or documentation kebab-case rules."""
    if target_file.name in SKIP_GOVERNANCE_FILES:
        return None
    for line in content.splitlines():
        if not any(marker in line for marker in SAFE_PLACEHOLDERS):
            for pattern, label in SECRET_PATTERNS:
                if re.search(pattern, line):
                    return f"🛡️ Sentinel Hook Blocked Edit: Detected plaintext {label} in '{target_file.name}'."
    try:
        parts = target_file.resolve().relative_to(repo_root.resolve()).parts
    except ValueError:
        return None
    if not parts:
        return None
    if len(parts) == 1 and parts[0].lower().endswith(".md") and parts[0] not in {"README.md", "AGENTS.md"}:
        return f"📚 DocDoc Hook Blocked Edit: Unauthorized root markdown '{parts[0]}' (only README.md/AGENTS.md)."
    if parts[0].lower() == "documentation":
        for sub in parts[1:-1]:
            if sub != ".organization_discrete" and (any(c.isupper() for c in sub) or "_" in sub):
                return f"📚 DocDoc Hook Blocked Edit: Directory '{sub}' in documentation/ must be lowercase kebab-case."
        if parts[-1].lower().endswith(".md"):
            stem = Path(parts[-1]).stem
            if any(c.isupper() for c in stem) or "_" in stem:
                return f"📚 DocDoc Hook Blocked Edit: File '{parts[-1]}' in documentation/ must be lowercase kebab-case."
    return None


FILE_EDIT_TOOLS = {
    "write_file",
    "edit_file",
    "write_to_file",
    "replace_file_content",
    "multi_replace_file_content",
}


def handle_pre_tool_use(payload: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    """Evaluate PreToolUse hook payload and return allow, ask, or deny decision."""
    tool_call = payload.get("toolCall") or {}
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args") or {}
    if tool_name == "run_command":
        cmd = str(args.get("CommandLine", ""))
        for pattern, label in DESTRUCTIVE_CMD_PATTERNS:
            if re.search(pattern, cmd):
                return {"decision": "ask", "reason": f"⚠️ Nexus Safety Hook: Confirm {label}."}
        return {"decision": "allow"}
    raw_target = args.get("Path") or args.get("TargetFile")
    if tool_name in FILE_EDIT_TOOLS and raw_target:
        target_path = Path(str(raw_target))
        chunks = args.get("ReplacementChunks") or []
        chunk_text = "\n".join(str(c.get("ReplacementContent", "")) for c in chunks if isinstance(c, dict))
        content = str(
            args.get("Content")
            or args.get("Replacement")
            or args.get("CodeContent")
            or args.get("ReplacementContent")
            or chunk_text
            or ""
        )
        violation = validate_file_governance(target_path, content, repo_root)
        if violation:
            return {"decision": "deny", "reason": violation}
        snapshot_before_edit(target_path, repo_root)
    return {"decision": "allow"}


def main() -> int:
    """Entrypoint for Antigravity lifecycle hooks."""
    event = sys.argv[1].lower() if len(sys.argv) > 1 else "pre-tool-use"
    repo_root = resolve_repo_root()
    if event == "pre-tool-use":
        raw_stdin = "" if sys.stdin.isatty() else sys.stdin.read().strip()
        try:
            payload = json.loads(raw_stdin) if raw_stdin else {}
        except json.JSONDecodeError:
            payload = {}
        print(json.dumps(handle_pre_tool_use(payload, repo_root)))
        return 0
    sweep_stray_backups(repo_root)
    if event == "stop":
        try:
            from log_run import log_agent_run

            log_agent_run(repo_root, "antigravity-hook", "Completed agent turn (Stop hook)", "SUCCESS")
        except (ImportError, OSError) as exc:
            sys.stderr.write(f"Stop hook log warning: {exc}\n")
        print(json.dumps({"decision": "allow"}))
        return 0
    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
