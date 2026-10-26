#!/usr/bin/env python3
"""
Composite Persona Prompt Builder & Local Runner (`prompt`, `run`) (< 200 lines).
Supports `.agents/roster/<agent>.md`, `.agents/agents/<agent>.md`, and `.jules/<agent>.md`.
"""

from __future__ import annotations

from pathlib import Path
import subprocess  # nosec B404
import sys
from typing import List, Optional

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cli_agents.env_git import resolve_project_root, resolve_system_config_dir  # noqa: E402
from cli_logger import cli_err, cli_out  # noqa: E402
from porter_persona_roster import PERSONA_ROSTER  # noqa: E402


def strip_yaml_frontmatter(markdown_text: str) -> str:
    """Remove YAML frontmatter from an agent `.md` file when constructing a Jules session prompt."""
    lines = markdown_text.splitlines()
    if lines and lines[0].strip() == "---":
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                return "\n".join(lines[idx + 1 :]).strip()
    return markdown_text.strip()


def _resolve_agent_definition_file(
    project_root: Path, system_root: Path, agent: str
) -> Optional[Path]:
    """Locate the persona definition in `.agents/roster/`, `.agents/agents/`, or system config."""
    candidates = (
        project_root / ".agents" / "roster" / f"{agent}.md",
        project_root / ".agents" / "agents" / f"{agent}.md",
        system_root / "agents" / f"{agent}.md",
    )
    for path in candidates:
        if path.exists():
            return path
    return None


def build_composite_prompt(agent: str, task: Optional[str] = None) -> str:
    """
    Assemble the full composite prompt combining:
      1. The 1-line Google Jules persona signature header
      2. The Assigned Task
      3. The Agent's System Prompt & Core Directives (`.agents/roster/<agent>.md` or `.agents/agents/<agent>.md`)
      4. The Live Operational Playbook (`.jules/<agent>.md`)
      5. Mandatory Verification Gate instructions
    """
    if agent not in PERSONA_ROSTER:
        raise ValueError(
            f"Unknown agent '{agent}'. Choose from: {', '.join(PERSONA_ROSTER.keys())}"
        )

    project_root = resolve_project_root()
    system_root = resolve_system_config_dir()
    spec = PERSONA_ROSTER[agent]

    first_line = f"{spec.jules_header} | Task: {task}" if task else spec.jules_header
    sections: List[str] = [first_line, ""]

    if task:
        sections.append(f"## Assigned Task\n{task}\n")

    agent_md_path = _resolve_agent_definition_file(project_root, system_root, agent)
    if agent_md_path:
        sections.append(strip_yaml_frontmatter(agent_md_path.read_text(encoding="utf-8")))

    if spec.jules_file:
        jules_path = project_root / ".jules" / spec.jules_file
        if not jules_path.exists():
            jules_path = system_root / "jules" / spec.jules_file
        if jules_path.exists():
            sections.append(f"\n## Live Operational Playbook (`.jules/{spec.jules_file}`)\n")
            sections.append(jules_path.read_text(encoding="utf-8").strip())
            sections.append(
                "\n## Journal Update Requirement\n"
                "If you discover a new vulnerability, performance bottleneck, or architectural pattern "
                f"during this session, append a concise dated entry (`## YYYY-MM-DD - Title`) to `.jules/{spec.jules_file}`."
            )

    sections.append(
        "\n## Mandatory Verification Gate\n"
        "Before completing your session or opening a pull request, run:\n"
        "```bash\n"
        f"make {spec.make_target}\n"
        "# or:\n"
        f"uv run python scripts/porter_cli_agents.py verify {agent}\n"
        "```\n"
        "Ensure zero regressions and archive any temporary `.bk` backup files into `.legacy_hr/`."
    )
    return "\n".join(sections)


def cmd_prompt(agent: str, task: Optional[str]) -> int:
    """Output the composite prompt for an agent so it can be piped to `jules new` or `agy`."""
    try:
        cli_out(build_composite_prompt(agent, task))
        return 0
    except ValueError as exc:
        cli_err(f"❌ Error: {exc}")
        return 1


def cmd_run(
    agent: str, task: str, engine: str, repo: Optional[str] = None, parallel: int = 1
) -> int:
    """Dispatch a task to a persona via Antigravity CLI (`agy`), Google `jules` CLI, or stdout."""
    if agent not in PERSONA_ROSTER:
        cli_err(f"❌ Error: Unknown agent '{agent}'.")
        return 1

    if engine == "print":
        return cmd_prompt(agent, task)

    if engine == "jules":
        from cli_agents.jules_dispatch import cmd_jules_dispatch

        return cmd_jules_dispatch(
            agent=agent, task=task, repo=repo, parallel=parallel, dry_run=False
        )

    if engine == "agy":
        cmd = ["agy", "--agent", agent, task]
        cli_out(f"🚀 Launching Antigravity CLI with agent '{agent}': {' '.join(cmd)}")
        try:
            return subprocess.run(cmd, check=False).returncode  # nosec B603
        except FileNotFoundError:
            cli_err(
                "⚠️  'agy' executable not found on PATH. Outputting composite prompt instead:\n"
            )
            return cmd_prompt(agent, task)

    cli_err(f"❌ Unknown engine '{engine}'.")
    return 1
