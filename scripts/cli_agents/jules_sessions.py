#!/usr/bin/env python3
"""Google Jules Remote Session Listing & Filtering (`list`, `jules-sessions`, `jules-repos`) (< 200 lines)."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess  # nosec B404
import sys
from typing import Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cli_agents.env_git import (  # noqa: E402
    is_current_branch_pushed_to_origin,
    resolve_current_git_branch,
    resolve_github_repo,
    resolve_jules_executable,
    resolve_project_root,
    resolve_system_config_dir,
)
from cli_logger import cli_err, cli_out  # noqa: E402
from porter_persona_roster import (  # noqa: E402
    PERSONA_ROSTER,
    JulesSessionRow,
    detect_persona_from_description,
)

ROW_PATTERN = re.compile(
    r"^\s*(\d+)\s+(.+?)\s+([A-Za-z0-9_.-]+/\S+)\s+(\d+(?:\s+[A-Za-z]+)?(?:\s+ago)?|\S+)\s*(.*)$"
)


def fetch_parsed_jules_sessions() -> Tuple[str, List[JulesSessionRow]]:
    """Query `jules remote list --session` and parse each row into `JulesSessionRow` objects."""
    jules_bin = resolve_jules_executable()
    if not jules_bin:
        return "", []
    res = subprocess.run(  # nosec B603
        [jules_bin, "remote", "list", "--session"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    lines = (
        [ln for ln in (res.stdout or "").splitlines() if ln.strip()] if res.returncode == 0 else []
    )
    if not lines:
        return "", []
    parsed_rows: List[JulesSessionRow] = []
    for raw in lines[1:]:
        m = ROW_PATTERN.match(raw)
        if m:
            g = [m.group(i).strip() for i in range(1, 6)]
            persona = detect_persona_from_description(g[1])
            row = JulesSessionRow(g[0], g[1], g[2], g[3], g[4] or "Completed", raw, persona)
        else:
            parts = raw.strip().split()
            sid = parts[0] if parts and parts[0].isdigit() else "unknown"
            row = JulesSessionRow(
                sid, raw.strip(), "", "", "", raw, detect_persona_from_description(raw)
            )
        parsed_rows.append(row)
    return lines[0], parsed_rows


def repo_matches_filter(row_repo: str, row_raw: str, repo_filter: str) -> bool:
    """Match `--repo` filter even when `jules` truncates the Repo column in its table output."""
    filt = repo_filter.strip().lower()
    if filt in row_raw.lower():
        return True
    cleaned = row_repo.lower().rstrip("…").rstrip(".")
    owner, short = filt.split("/", 1) if "/" in filt else ("", filt)
    if cleaned and "/" in cleaned:
        row_owner, row_short = cleaned.split("/", 1)
        return (not owner or owner == row_owner) and (
            short.startswith(row_short) or row_short.startswith(short[:12])
        )
    return False


def cmd_list() -> int:
    """Display a formatted roster table of all 12 CLI agents and latest Jules Session IDs."""
    project_root, system_root = resolve_project_root(), resolve_system_config_dir()
    git_branch = resolve_current_git_branch(project_root)
    pushed = "pushed" if is_current_branch_pushed_to_origin(project_root) else "local"
    default_repo = resolve_github_repo(project_root)
    _, all_sessions = fetch_parsed_jules_sessions()
    latest: Dict[str, JulesSessionRow] = {}
    for r in all_sessions:
        if (
            r.matched_persona
            and r.matched_persona not in latest
            and repo_matches_filter(r.repo, r.raw_line, default_repo)
        ):
            latest[r.matched_persona] = r

    cli_out(
        f"🏛️  PORTER CLI ROSTER | Branch: {git_branch} ({pushed}) | Jules: {'READY' if resolve_jules_executable() else 'MISSING'}"
    )
    for name, spec in PERSONA_ROSTER.items():
        p_ok = (project_root / ".agents" / "roster" / f"{name}.md").exists() or (
            project_root / ".agents" / "agents" / f"{name}.md"
        ).exists()
        s_ok = (system_root / "agents" / f"{name}.md").exists()
        lat = latest.get(name)
        l_id, l_st = (
            (lat.session_id, f"{lat.status} ({lat.last_active})"[:18]) if lat else ("-", "-")
        )
        cli_out(
            f"{spec.emoji} {name:<15} {spec.category:<14} {'✅' if p_ok else '❌'} {'✅' if s_ok else '❌'} {spec.jules_file or '(constitution)':<14} {l_id:<20} {l_st:<18}"
        )
    return 0


def cmd_jules_sessions(
    persona: Optional[str] = None,
    repo: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 25,
) -> int:
    """List remote Google Jules sessions with truncation-safe repo filtering and persona tags."""
    header, rows = fetch_parsed_jules_sessions()
    if not rows:
        cli_out("No remote Jules sessions found.")
        return 0
    p_low, s_low = (persona or "").lower().strip(), (status or "").lower()
    filtered = [
        r
        for r in rows
        if (not p_low or r.matched_persona == p_low or p_low in r.raw_line.lower())
        and (not repo or repo_matches_filter(r.repo, r.raw_line, repo))
        and (not s_low or s_low in r.status.lower() or s_low in r.raw_line.lower())
    ]
    cli_out(f"PERSONA        {header}")
    for row in filtered[:limit]:
        spec = PERSONA_ROSTER.get(row.matched_persona or "")
        cli_out(
            f"{f'{spec.emoji} {row.matched_persona}' if spec else '🤖 (custom)':<14} {row.raw_line}"
        )
    return 0


def cmd_jules_repos() -> int:
    """List all GitHub repositories connected to Google Jules CLI."""
    jules_bin = resolve_jules_executable()
    if not jules_bin:
        cli_err("❌ Error: Google Jules CLI ('jules') not found.")
        return 1
    return subprocess.run(
        [jules_bin, "remote", "list", "--repo"], check=False
    ).returncode  # nosec B603


from cli_agents.jules_actions import (  # noqa: E402, F401
    cmd_jules_pull,
    cmd_jules_teleport,
    resolve_session_target,
)
