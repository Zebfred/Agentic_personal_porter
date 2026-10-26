#!/usr/bin/env python3
"""
Google Jules Single & Parallel Batch Dispatcher (`jules-dispatch`, `jules-dispatch-batch`) (< 200 lines).
Automatically records every dispatch in `.jules/activity.log`.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import subprocess  # nosec B404
import sys
from typing import Dict, List, Optional, Sequence, Tuple

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cli_agents.env_git import (  # noqa: E402
    log_jules_activity,
    resolve_dispatch_cwd,
    resolve_github_repo,
    resolve_jules_executable,
    resolve_project_root,
)
from cli_agents.prompt_builder import build_composite_prompt  # noqa: E402
from cli_logger import cli_err, cli_out  # noqa: E402
from porter_persona_roster import PERSONA_ROSTER  # noqa: E402


def cmd_jules_dispatch(
    agent: str,
    task: Optional[str] = None,
    repo: Optional[str] = None,
    parallel: int = 1,
    dry_run: bool = False,
) -> int:
    """Dispatch a persona-aligned coding session to Google Jules CLI (`jules new`)."""
    if agent not in PERSONA_ROSTER:
        cli_err(f"❌ Error: Unknown agent '{agent}'.")
        return 1
    project_root = resolve_project_root()
    spec = PERSONA_ROSTER[agent]
    effective_task = task.strip() if task and task.strip() else spec.default_task
    resolved_repo = resolve_github_repo(project_root, repo)
    composite_prompt = build_composite_prompt(agent, effective_task)
    jules_bin = resolve_jules_executable()
    dispatch_cwd = resolve_dispatch_cwd(project_root)

    if dry_run:
        cli_out(
            f"🧪 [DRY RUN] Google Jules Dispatch Preview for {spec.emoji} {spec.title} -> {resolved_repo}"
        )
        cli_out(composite_prompt)
        log_jules_activity(project_root, "dispatch-dry-run", agent, f"repo={resolved_repo}")
        return 0
    if not jules_bin:
        cli_err("❌ Error: Google Jules CLI ('jules') not found.")
        return 1

    cmd: List[str] = [
        jules_bin,
        "new",
        "--repo",
        resolved_repo,
        *(["--parallel", str(parallel)] if parallel > 1 else []),
    ]
    cli_out(f"🚀 Dispatching {spec.emoji} {spec.title} to Google Jules (repo: {resolved_repo})...")
    res = subprocess.run(
        cmd, input=composite_prompt, text=True, encoding="utf-8", cwd=str(dispatch_cwd), check=False
    )  # nosec B603
    log_jules_activity(project_root, "dispatch", agent, f"repo={resolved_repo} rc={res.returncode}")
    return res.returncode


def _dispatch_single_worker(
    agent: str,
    task: Optional[str],
    resolved_repo: str,
    jules_bin: str,
    dispatch_cwd: Path,
    project_root: Path,
) -> Tuple[str, int, str]:
    """Worker function for parallel multi-persona dispatch using direct `jules` binary."""
    spec = PERSONA_ROSTER[agent]
    effective_task = task.strip() if task and task.strip() else spec.default_task
    composite_prompt = build_composite_prompt(agent, effective_task)
    res = subprocess.run(  # nosec B603
        [jules_bin, "new", "--repo", resolved_repo],
        input=composite_prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(dispatch_cwd),
        check=False,
    )
    output = (res.stdout or "") + (f"\n{res.stderr}" if res.stderr else "")
    session_id, url = "unknown", ""
    for line in output.splitlines():
        if line.strip().startswith("ID:"):
            session_id = line.split("ID:", 1)[1].strip()
        elif line.strip().startswith("URL:"):
            url = line.split("URL:", 1)[1].strip()
    log_jules_activity(
        project_root, "batch-dispatch", agent, f"session={session_id} rc={res.returncode}"
    )
    st = "✅ CREATED" if res.returncode == 0 else "❌ FAILED"
    return (
        agent,
        res.returncode,
        f"{spec.emoji} {agent:<15} | Status: {st} | ID: {session_id:<20} | {url or output.strip()[:80]}",
    )


def _expand_batch_agents(agents: Sequence[str]) -> Optional[List[str]]:
    """Expand preset groups ('new', 'roster') or validate individual persona names."""
    expanded: List[str] = []
    for item in agents:
        key = item.lower().strip()
        if key == "new":
            expanded.extend(["archie", "docdoc", "dave", "crii", "jovol"])
        elif key == "roster":
            expanded.extend(
                ["sentinel", "bolt", "palette", "archie", "docdoc", "dave", "crii", "jovol"]
            )
        elif key in PERSONA_ROSTER:
            expanded.append(key)
        else:
            cli_err(f"❌ Error: Unknown persona or group '{item}'.")
            return None
    return list(dict.fromkeys(expanded))


def cmd_jules_dispatch_batch(
    agents: Sequence[str],
    repo: Optional[str] = None,
    task_override: Optional[str] = None,
    dry_run: bool = False,
) -> int:
    """Dispatch multiple personas in parallel to Google Jules CLI using `ThreadPoolExecutor`."""
    target_agents = _expand_batch_agents(agents)
    if not target_agents:
        return 1
    project_root = resolve_project_root()
    resolved_repo = resolve_github_repo(project_root, repo)
    if dry_run:
        cli_out(
            f"🧪 [DRY RUN] Parallel Batch Dispatch ({len(target_agents)} Personas) -> {resolved_repo}"
        )
        for agent in target_agents:
            cli_out(
                f"  • {PERSONA_ROSTER[agent].emoji} {agent:<15} : {task_override or PERSONA_ROSTER[agent].default_task}"
            )
        return 0

    jules_bin = resolve_jules_executable()
    if not jules_bin:
        cli_err("❌ Error: Google Jules CLI ('jules') not found.")
        return 1
    dispatch_cwd = resolve_dispatch_cwd(project_root)
    results_by_agent: Dict[str, Tuple[str, int, str]] = {}
    with ThreadPoolExecutor(max_workers=min(len(target_agents), 6)) as pool:
        f_map = {
            pool.submit(
                _dispatch_single_worker,
                a,
                task_override,
                resolved_repo,
                jules_bin,
                dispatch_cwd,
                project_root,
            ): a
            for a in target_agents
        }
        for future in as_completed(f_map):
            name, code, summary = future.result()
            results_by_agent[name] = (name, code, summary)

    for agent in target_agents:
        cli_out(f"   {results_by_agent[agent][2]}")
    return 0 if all(results_by_agent[a][1] == 0 for a in target_agents) else 1
