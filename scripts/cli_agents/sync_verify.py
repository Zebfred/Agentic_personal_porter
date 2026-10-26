#!/usr/bin/env python3
"""
Cross-Surface Agent Sync, Verification Gates & Playbook Learning (`sync`, `verify`, `learn`) (< 200 lines).
"""

from __future__ import annotations

import datetime
from pathlib import Path
import shutil
import subprocess  # nosec B404
import sys
from typing import Dict, List, Optional, Sequence, Tuple

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cli_agents.env_git import (  # noqa: E402
    log_jules_activity,
    resolve_current_git_branch,
    resolve_project_root,
    resolve_system_config_dir,
)
from cli_logger import cli_err, cli_out  # noqa: E402
from porter_persona_roster import PERSONA_ROSTER  # noqa: E402


def backup_to_legacy_hr(target_file: Path, project_root: Path) -> Optional[Path]:
    """Create a `.bk` backup of an existing file and archive it into `.legacy_hr/DDMMYYYY/`."""
    if not target_file.exists():
        return None
    legacy_dir = project_root / ".legacy_hr" / datetime.datetime.now().strftime("%d%m%Y")
    legacy_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = legacy_dir / f"{target_file.name}.{stamp}.bk"
    shutil.copy2(target_file, backup_path)
    return backup_path


def sync_file_pair(
    project_file: Path, system_file: Path, direction: str, project_root: Path
) -> str:
    """Synchronize a single file between project and system directories with `.bk` archiving."""
    p_ok, s_ok = project_file.exists(), system_file.exists()
    if not p_ok and not s_ok:
        return "MISSING_BOTH"
    if p_ok and s_ok:
        if project_file.read_bytes() == system_file.read_bytes():
            return "IN_SYNC"
        to_sys = direction == "project-to-system" or (
            direction == "both" and project_file.stat().st_mtime >= system_file.stat().st_mtime
        )
        src, dst = (project_file, system_file) if to_sys else (system_file, project_file)
        backup_to_legacy_hr(dst, project_root)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return "SYNCED_PROJ->SYS" if to_sys else "SYNCED_SYS->PROJ"
    if p_ok and direction in ("both", "project-to-system"):
        system_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(project_file, system_file)
        return "INSTALLED_TO_SYSTEM"
    if s_ok and direction in ("both", "system-to-project"):
        project_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(system_file, project_file)
        return "RESTORED_TO_PROJECT"
    return "SKIPPED"


def cmd_sync(direction: str) -> int:
    """Synchronize all 12 CLI agent definitions, `.agents/roster/`, and `.jules` playbooks."""
    project_root, system_root = resolve_project_root(), resolve_system_config_dir()
    p_agents, p_roster = project_root / ".agents" / "agents", project_root / ".agents" / "roster"
    s_agents, p_jules, s_jules = (
        system_root / "agents",
        project_root / ".jules",
        system_root / "jules",
    )
    for d in (p_agents, p_roster, s_agents, p_jules, s_jules):
        d.mkdir(parents=True, exist_ok=True)

    cli_out(f"🔄 Synchronizing Porter CLI Agents (direction: {direction})")
    cli_out(f"   Active Branch: {resolve_current_git_branch(project_root)}\n")
    for name, spec in PERSONA_ROSTER.items():
        st = sync_file_pair(
            p_agents / f"{name}.md", s_agents / f"{name}.md", direction, project_root
        )
        cli_out(f"   {spec.emoji} {name:<16} -> {st}")
        if spec.jules_file:
            jst = sync_file_pair(
                p_jules / spec.jules_file, s_jules / spec.jules_file, direction, project_root
            )
            cli_out(f"   {spec.emoji} {spec.jules_file:<16} -> {jst}")

    for sname in ("porter_persona_roster.py", "porter_cli_agents.py"):
        src_p, dst_p = project_root / "scripts" / sname, s_agents / sname
        if src_p.exists() and src_p.resolve() != dst_p.resolve():
            shutil.copy2(src_p, dst_p)
    log_jules_activity(project_root, "sync", "roster", f"direction={direction}")
    cli_out("\n✅ Synchronization complete!")
    return 0


def run_step(description: str, cmd: Sequence[str], cwd: Path) -> bool:
    """Run a single verification subprocess and stream its output."""
    cli_out(f"   ▶ {description}: {' '.join(cmd)}")
    try:
        return subprocess.run(cmd, cwd=str(cwd), check=False).returncode == 0  # nosec B603
    except FileNotFoundError as exc:
        cli_err(f"   ❌ Executable not found while running '{cmd[0]}': {exc}")
        return False


def _persona_command_map(py: str, project_root: Path) -> Dict[str, List[Tuple[str, List[str]]]]:
    """Build verification command lists keyed by persona name."""
    npm_cmd = "npm.cmd" if sys.platform.startswith("win") else "npm"
    t_mypy = "src/schemas" if (project_root / "src" / "schemas").exists() else "src"
    an_dir = project_root / "scripts" / "analyze_scripts"
    crii_t = [
        t
        for t in ("tests/unit/test_api_schemas.py", "tests/unit/test_mock_mongo.py")
        if (project_root / t).exists()
    ] or ["tests/unit"]
    return {
        "sentinel": [
            (
                "Sentinel Suite",
                [py, "-m", "pytest", "tests/unit", "-k", "auth or security or mock_mongo", "-q"],
            )
        ],
        "bolt": [("Bolt Suite", [py, "-m", "pytest", "tests/unit/test_mock_mongo.py", "-q"])],
        "palette": [("Palette CSS Build", [npm_cmd, "run", "build:css"])],
        "archie": [
            ("Archie Ruff", [py, "-m", "ruff", "check", "src"]),
            ("Archie Mypy", [py, "-m", "mypy", t_mypy]),
        ],
        "docdoc": [("DocDoc Hygiene", [py, str(an_dir / "verify_doc_hygiene.py")])],
        "dave": [("Dave DevOps", [py, str(an_dir / "verify_devops.py")])],
        "crii": [("Crii Suite", [py, "-m", "pytest", *crii_t, "-q"])],
        "jovol": [("Jovol Components", [py, str(an_dir / "verify_components.py")])],
        "silas": [
            ("Silas Ruff", [py, "-m", "ruff", "check", "src", "tests"]),
            ("Silas Mypy", [py, "-m", "mypy", "src"]),
            ("Silas Pytest", [py, "-m", "pytest", "tests/unit", "-q"]),
        ],
    }


def verify_single_persona(agent: str, project_root: Path) -> bool:
    """Execute the automated verification checks for a single persona."""
    spec = PERSONA_ROSTER[agent]
    cli_out(f"\n{spec.emoji} Verifying {spec.title}...")
    steps = _persona_command_map(sys.executable, project_root).get(agent)
    if steps:
        return all(run_step(desc, cmd, project_root) for desc, cmd in steps)
    return (
        all(verify_single_persona(p, project_root) for p in spec.partners)
        if spec.partners
        else True
    )


def cmd_verify(target: str) -> int:
    """Run verification gates for a specific persona, 'roster' (8 Jules agents), or 'all'."""
    project_root = resolve_project_root()
    if target == "roster":
        targets = ["sentinel", "bolt", "palette", "archie", "docdoc", "dave", "crii", "jovol"]
    elif target == "all":
        targets = list(PERSONA_ROSTER.keys())
    elif target in PERSONA_ROSTER:
        targets = [target]
    else:
        cli_err(f"❌ Error: Unknown persona '{target}'.")
        return 1
    results = [(name, verify_single_persona(name, project_root)) for name in targets]
    for name, passed in results:
        cli_out(
            f"   {PERSONA_ROSTER[name].emoji} {name:<16} : {'✅ PASSED' if passed else '❌ FAILED'}"
        )
    log_jules_activity(project_root, "verify", target, f"passed={all(p for _, p in results)}")
    return 0 if all(p for _, p in results) else 1


def cmd_learn(agent: str, title: str, learning: str, action: str) -> int:
    """Append a dated learning entry to `.jules/<agent>.md` and sync to system config."""
    if agent not in PERSONA_ROSTER or not PERSONA_ROSTER[agent].jules_file:
        cli_err(f"❌ Error: Agent '{agent}' does not have a dedicated .jules/*.md playbook.")
        return 1
    project_root = resolve_project_root()
    jules_path = project_root / ".jules" / str(PERSONA_ROSTER[agent].jules_file)
    backup_to_legacy_hr(jules_path, project_root)
    today = datetime.date.today().isoformat()
    k1, k2 = ("Vulnerability", "Prevention") if agent == "sentinel" else ("Learning", "Action")
    with open(jules_path, "a", encoding="utf-8") as handle:
        handle.write(f"\n## {today} - {title}\n**{k1}:** {learning}\n**{k2}:** {action}\n")
    log_jules_activity(project_root, "learn", agent, f"title={title}")
    return cmd_sync(direction="project-to-system")
