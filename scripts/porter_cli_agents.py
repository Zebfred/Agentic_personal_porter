#!/usr/bin/env python3
"""
Porter True CLI Agents — Thin CLI Router & Public Facade (< 200 lines, < 60L functions).
Subcommand implementations reside in `scripts/cli_agents/`.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Optional, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from cli_agents.env_git import (  # noqa: E402, F401
    is_current_branch_pushed_to_origin,
    log_jules_activity,
    resolve_current_git_branch,
    resolve_dispatch_cwd,
    resolve_github_repo,
    resolve_jules_executable,
    resolve_project_root,
    resolve_system_config_dir,
)
from cli_agents.jules_dispatch import (  # noqa: E402, F401
    cmd_jules_dispatch,
    cmd_jules_dispatch_batch,
)
from cli_agents.jules_sessions import (  # noqa: E402, F401
    cmd_jules_pull,
    cmd_jules_repos,
    cmd_jules_sessions,
    cmd_jules_teleport,
    cmd_list,
    fetch_parsed_jules_sessions,
    repo_matches_filter,
    resolve_session_target,
)
from cli_agents.prompt_builder import (  # noqa: E402, F401
    build_composite_prompt,
    cmd_prompt,
    cmd_run,
    strip_yaml_frontmatter,
)
from cli_agents.sync_verify import (  # noqa: E402, F401
    backup_to_legacy_hr,
    cmd_learn,
    cmd_sync,
    cmd_verify,
    run_step,
    sync_file_pair,
    verify_single_persona,
)
from porter_persona_roster import (  # noqa: E402, F401
    PERSONA_ROSTER,
    JulesSessionRow,
    detect_persona_from_description,
)

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def _register_core_subparsers(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Register `list`, `sync`, `verify`, `prompt`, `run`, and `learn` subcommands."""
    sub.add_parser("list", help="List all 12 CLI personas, active branch, and latest Session IDs")
    p_sync = sub.add_parser("sync", help="Synchronize CLI agents and .jules playbooks")
    p_sync.add_argument(
        "--direction", choices=["both", "project-to-system", "system-to-project"], default="both"
    )
    p_verify = sub.add_parser("verify", help="Run verification gate for a persona, 'roster', 'all'")
    p_verify.add_argument("target", help="Persona name or 'roster' / 'all'")

    p_prompt = sub.add_parser("prompt", help="Output composite prompt for a persona")
    p_prompt.add_argument("agent", choices=list(PERSONA_ROSTER.keys()))
    p_prompt.add_argument("--task", default=None)

    p_run = sub.add_parser("run", help="Run a task with a CLI persona via agy, jules, or stdout")
    p_run.add_argument("agent", choices=list(PERSONA_ROSTER.keys()))
    p_run.add_argument("task")
    p_run.add_argument("--engine", choices=["agy", "jules", "print"], default="agy")
    p_run.add_argument("--repo", default=None)
    p_run.add_argument("--parallel", type=int, default=1)

    p_learn = sub.add_parser("learn", help="Append a new learning to .jules/<agent>.md")
    p_learn.add_argument("agent", choices=[k for k, v in PERSONA_ROSTER.items() if v.jules_file])
    p_learn.add_argument("--title", required=True)
    p_learn.add_argument("--learning", required=True)
    p_learn.add_argument("--action", required=True)


def _register_jules_subparsers(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Register Google Jules remote dispatch, session listing, pull, and teleport subcommands."""
    p_jdisp = sub.add_parser("jules-dispatch", help="Dispatch a persona session to Google Jules")
    p_jdisp.add_argument("agent", choices=list(PERSONA_ROSTER.keys()))
    p_jdisp.add_argument("task", nargs="?", default=None)
    p_jdisp.add_argument("--repo", default=None)
    p_jdisp.add_argument("--parallel", type=int, default=1)
    p_jdisp.add_argument("--dry-run", action="store_true")

    p_jbatch = sub.add_parser("jules-dispatch-batch", help="Dispatch multiple personas in parallel")
    p_jbatch.add_argument("agents", nargs="+")
    p_jbatch.add_argument("--repo", default=None)
    p_jbatch.add_argument("--task", default=None)
    p_jbatch.add_argument("--dry-run", action="store_true")

    p_jsess = sub.add_parser("jules-sessions", help="List and filter remote Google Jules sessions")
    p_jsess.add_argument("--persona", default=None)
    p_jsess.add_argument("--repo", default=None)
    p_jsess.add_argument("--status", default=None)
    p_jsess.add_argument("--limit", type=int, default=25)

    sub.add_parser("jules-repos", help="List GitHub repositories connected to Google Jules")
    for cmd_name in ("jules-pull", "jules-teleport"):
        p_sub = sub.add_parser(cmd_name, help=f"Execute {cmd_name} by Session ID or Persona Name")
        p_sub.add_argument("session_id")
        if cmd_name == "jules-pull":
            p_sub.add_argument("--apply", action="store_true")
        p_sub.add_argument(
            "--verify", choices=list(PERSONA_ROSTER.keys()) + ["roster", "all"], default=None
        )


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="porter-agent",
        description="True CLI Agent Manager & Google Jules Integrator for Agentic Personal Porter",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    _register_core_subparsers(sub)
    _register_jules_subparsers(sub)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entrypoint routing parsed subcommands to modular handlers."""
    args = build_parser().parse_args(argv)
    handlers = {
        "list": lambda: cmd_list(),
        "sync": lambda: cmd_sync(direction=args.direction),
        "verify": lambda: cmd_verify(target=args.target),
        "prompt": lambda: cmd_prompt(agent=args.agent, task=args.task),
        "run": lambda: cmd_run(args.agent, args.task, args.engine, args.repo, args.parallel),
        "jules-dispatch": lambda: cmd_jules_dispatch(
            args.agent, args.task, args.repo, args.parallel, args.dry_run
        ),
        "jules-dispatch-batch": lambda: cmd_jules_dispatch_batch(
            args.agents, args.repo, args.task, args.dry_run
        ),
        "jules-sessions": lambda: cmd_jules_sessions(
            args.persona, args.repo, args.status, args.limit
        ),
        "jules-repos": lambda: cmd_jules_repos(),
        "jules-pull": lambda: cmd_jules_pull(
            args.session_id, apply_patch=args.apply, verify_agent=args.verify
        ),
        "jules-teleport": lambda: cmd_jules_teleport(args.session_id, verify_agent=args.verify),
        "learn": lambda: cmd_learn(args.agent, args.title, args.learning, args.action),
    }
    return handlers[args.command]() if args.command in handlers else 0


if __name__ == "__main__":
    sys.exit(main())
