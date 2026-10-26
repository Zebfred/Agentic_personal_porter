#!/usr/bin/env python3
"""Google Jules Session Resolution, Pull & Teleport Actions (< 200 lines)."""

from __future__ import annotations

from pathlib import Path
import subprocess  # nosec B404
import sys
from typing import Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cli_agents.env_git import (  # noqa: E402
    log_jules_activity,
    resolve_github_repo,
    resolve_jules_executable,
    resolve_project_root,
)
from cli_agents.jules_sessions import (  # noqa: E402
    fetch_parsed_jules_sessions,
    repo_matches_filter,
)
from cli_agents.sync_verify import cmd_verify  # noqa: E402
from cli_logger import cli_err  # noqa: E402
from porter_persona_roster import PERSONA_ROSTER  # noqa: E402


def resolve_session_target(session_or_persona: str) -> Tuple[Optional[str], Optional[str]]:
    """Resolve a numeric Session ID, 'latest', or a persona name into `(session_id, matched_persona)`."""
    cleaned, key = session_or_persona.strip(), session_or_persona.strip().lower()
    default_repo = resolve_github_repo(resolve_project_root())
    _, rows = fetch_parsed_jules_sessions()
    if cleaned.isdigit():
        return cleaned, next((r.matched_persona for r in rows if r.session_id == cleaned), None)
    if key == "latest":
        m = next(
            (r for r in rows if repo_matches_filter(r.repo, r.raw_line, default_repo)),
            rows[0] if rows else None,
        )
        return (m.session_id, m.matched_persona) if m else (None, None)
    if key in PERSONA_ROSTER:
        for r in rows:
            if (
                r.matched_persona == key
                and repo_matches_filter(r.repo, r.raw_line, default_repo)
                and "failed" not in r.status.lower()
            ):
                return r.session_id, key
        m = next((r for r in rows if r.matched_persona == key), None)
        return (m.session_id, key) if m else (None, key)
    return None, None


def _execute_session_action(
    action: str, session_or_persona: str, apply_patch: bool, verify_agent: Optional[str]
) -> int:
    """Shared execution helper for `jules-pull` and `jules-teleport`."""
    jules_bin = resolve_jules_executable()
    session_id, detected = resolve_session_target(session_or_persona) if jules_bin else (None, None)
    if not jules_bin or not session_id:
        cli_err(f"❌ Error resolving Google Jules session for '{session_or_persona}'.")
        return 1
    project_root = resolve_project_root()
    cmd = (
        [
            jules_bin,
            "remote",
            "pull",
            "--session",
            session_id,
            *(["--apply"] if apply_patch else []),
        ]
        if action == "pull"
        else [jules_bin, "teleport", session_id]
    )
    res = subprocess.run(cmd, cwd=str(project_root), check=False)  # nosec B603
    log_jules_activity(
        project_root, action, detected or "unknown", f"session={session_id} rc={res.returncode}"
    )
    if res.returncode != 0:
        return res.returncode
    eff = verify_agent or (
        detected if (action == "teleport" or apply_patch) and detected in PERSONA_ROSTER else None
    )
    return cmd_verify(eff) if eff else 0


def cmd_jules_pull(
    session_or_persona: str, apply_patch: bool = False, verify_agent: Optional[str] = None
) -> int:
    """Pull a remote Google Jules session diff by Session ID OR by Persona Name."""
    return _execute_session_action("pull", session_or_persona, apply_patch, verify_agent)


def cmd_jules_teleport(session_or_persona: str, verify_agent: Optional[str] = None) -> int:
    """Teleport local workspace to a Google Jules session and optionally verify."""
    return _execute_session_action("teleport", session_or_persona, False, verify_agent)
