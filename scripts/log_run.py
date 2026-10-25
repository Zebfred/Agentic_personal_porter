#!/usr/bin/env python3
"""Standardized Agent Run Logger & Tiered Retention Manager (log_run.py).

Records agent execution runs inside `.logs/DDMMYYYY/` and delegates the
4-Tier Date & Compression Lifecycle (`DDMMYYYY/` -> `MMYYYY/` -> `YYYY_{PROJECT}/`
-> `.tar.gz`) to `retention_engine.py` so scripts stay < 200 lines and
functions stay < 60 lines.
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional, Sequence, Tuple

from retention_engine import (
    archive_backup_file,
    get_daily_dir,
    resolve_repo_root,
    rotate_tiered_directory,
    sanitize_project_name,
    sweep_stray_backups_to_daily,
    sync_geminiignore_log_rules,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

__all__ = [
    "archive_backup_file",
    "get_daily_dir",
    "log_agent_run",
    "resolve_repo_root",
    "rotate_tiered_directory",
    "sanitize_project_name",
    "sweep_stray_backups_to_daily",
    "sync_geminiignore_log_rules",
]


def _execute_logged_command(command: str, repo_root: Path) -> Tuple[int, int, str]:
    """Run an optional shell command, returning `(exit_code, duration_ms, combined_output)`."""
    start_ns = time.perf_counter_ns()
    res = subprocess.run(
        command,
        cwd=str(repo_root),
        shell=True,  # noqa: S602 - intentional CLI wrapper for agent run logging
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    duration_ms = int((time.perf_counter_ns() - start_ns) / 1_000_000)
    output = (res.stdout or "") + ("\n" + res.stderr if res.stderr else "")
    return res.returncode, duration_ms, output


def log_agent_run(
    repo_root: Path,
    agent: str,
    task: str,
    status: str = "LOGGED",
    details: str = "",
    command: Optional[str] = None,
    now: Optional[datetime.datetime] = None,
) -> Tuple[int, Path]:
    """Record an agent run inside `.logs/DDMMYYYY/` and rotate `.logs/` & `.legacy_hr/`."""
    dt = now or datetime.datetime.now()
    project_name = sanitize_project_name(repo_root)
    logs_root = repo_root / ".logs"

    rotate_tiered_directory(logs_root, project_name, now=dt)
    rotate_tiered_directory(repo_root / ".legacy_hr", project_name, now=dt)
    sync_geminiignore_log_rules(repo_root, now=dt)

    daily_log_dir = get_daily_dir(logs_root, now=dt)
    exit_code, duration_ms, cmd_output = (0, 0, "")
    if command:
        exit_code, duration_ms, cmd_output = _execute_logged_command(command, repo_root)
        status = "SUCCESS" if exit_code == 0 else "FAILED"

    iso_ts = dt.isoformat(timespec="seconds")
    safe_agent = re.sub(r"[^a-zA-Z0-9_\-]", "_", agent.lower())
    record: Dict[str, Any] = {
        "timestamp": iso_ts, "date_dir": daily_log_dir.name, "project": project_name,
        "agent": agent, "task": task, "status": status, "exit_code": exit_code,
        "duration_ms": duration_ms, "command": command, "details": details,
    }
    with open(daily_log_dir / "agent_runs.jsonl", "a", encoding="utf-8") as jf:
        jf.write(json.dumps(record, ensure_ascii=False) + "\n")

    run_log_path = daily_log_dir / f"{dt.strftime('%H%M%S')}_{safe_agent}_run.log"
    lines = [
        "==================================================================",
        f"NEXUS AGENT RUN RECORD — {iso_ts}",
        "==================================================================",
        f"Project     : {project_name}",
        f"Agent       : {agent}",
        f"Task        : {task}",
        f"Status      : {status} (exit_code={exit_code}, duration={duration_ms}ms)",
    ]
    if command:
        lines.append(f"Command     : {command}")
    if details:
        lines.append(f"Details     : {details}")
    if cmd_output.strip():
        lines.extend(["", "--- Command Output ---", cmd_output.strip()])
    lines.append("==================================================================\n")
    run_log_path.write_text("\n".join(lines), encoding="utf-8")
    return exit_code, run_log_path


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint for recording agent runs, backing up files, and rotating `.logs/` & `.legacy_hr/`."""
    parser = argparse.ArgumentParser(description="Log agent runs into .logs/DDMMYYYY/ and manage 4-tier retention.")
    parser.add_argument("--repo-root", default=None, help="Target repository root.")
    parser.add_argument("--agent", default="antigravity", help="Agent persona name.")
    parser.add_argument("--task", default="", help="Brief description of the task or run.")
    parser.add_argument("--details", default="", help="Additional run notes.")
    parser.add_argument("--command", default=None, help="Optional shell command to execute, time, and derive status from.")
    parser.add_argument("--backup-file", default=None, help="Optional file path to snapshot in .legacy_hr/DDMMYYYY/.")
    parser.add_argument("--rotate-only", action="store_true", help="Only run 4-tier rotation and .geminiignore sync.")
    args = parser.parse_args(argv)

    repo_root = resolve_repo_root(args.repo_root)
    project_name = sanitize_project_name(repo_root)

    if args.backup_file:
        bk = archive_backup_file(Path(args.backup_file).resolve(), repo_root, copy_only=True)
        if bk:
            print(f"📦 Archived backup to: {bk.relative_to(repo_root)}")
            return 0
        print(f"⚠️ Target file not found or skipped: {args.backup_file}", file=sys.stderr)
        return 1

    if args.rotate_only:
        swept = sweep_stray_backups_to_daily(repo_root)
        hr_rep = rotate_tiered_directory(repo_root / ".legacy_hr", project_name)
        log_rep = rotate_tiered_directory(repo_root / ".logs", project_name)
        rules = sync_geminiignore_log_rules(repo_root)
        print(f"🔄 Rotation complete ({project_name}): swept={swept}, hr={hr_rep}, logs={log_rep}, ignore={rules}")
        return 0

    task = args.task or (f"Execute: {args.command}" if args.command else "Agent checkpoint")
    rc, log_path = log_agent_run(repo_root, args.agent, task, details=args.details, command=args.command)
    print(f"📝 Recorded agent run in: {log_path.relative_to(repo_root)}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
