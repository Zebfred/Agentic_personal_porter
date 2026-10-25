#!/usr/bin/env python3
"""
Porter True CLI Agents — Dispatcher, Google Jules Integrator, Verifier & Sync Tool.
See `documentation/architecture/jules-cli-runbook.md` for operational workflows and examples.
Persona definitions live in `scripts/porter_persona_roster.py`.
"""

# fmt: off
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime
import os
from pathlib import Path
import re
import shutil
import subprocess  # nosec B404
import sys
import tempfile
from typing import Dict, List, Optional, Sequence, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from porter_persona_roster import (  # noqa: E402
    PERSONA_ROSTER,
    JulesSessionRow,
    detect_persona_from_description,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def resolve_project_root() -> Path:
    """Locate the repository root from script location or current working directory."""
    script_path = Path(__file__).resolve()
    if (script_path.parents[1] / ".jules").exists() or (script_path.parents[1] / "Makefile").exists():
        return script_path.parents[1]

    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / ".jules").exists() and (candidate / "Makefile").exists():
            return candidate

    return script_path.parents[1]


def resolve_system_config_dir() -> Path:
    """Return the global CLI configuration directory from `PORTER_SYSTEM_CONFIG_DIR` or `~/.gemini/config`."""
    env_dir = os.environ.get("PORTER_SYSTEM_CONFIG_DIR")
    if env_dir:
        return Path(env_dir).expanduser()
    return Path.home() / ".gemini" / "config"


def resolve_jules_executable() -> Optional[str]:
    """
    Locate the native compiled `jules` binary first before falling back to wrapper scripts on `PATH`.
    Avoids `@google/jules/run.cjs` re-downloading the tarball into `%TEMP%/jules_tmp` on every run
    and prevents `Error: spawn EBUSY` during parallel dispatch.
    """
    env_bin = os.environ.get("PORTER_JULES_BIN")
    if env_bin:
        expanded = Path(env_bin).expanduser()
        if expanded.exists():
            return str(expanded)

    exe_name = "jules.exe" if sys.platform.startswith("win") else "jules"
    sys_bin_exe = resolve_system_config_dir() / "bin" / exe_name
    tmp_exe = Path(tempfile.gettempdir()) / "jules_tmp" / exe_name

    if tmp_exe.exists():
        try:
            sys_bin_exe.parent.mkdir(parents=True, exist_ok=True)
            if not sys_bin_exe.exists() or tmp_exe.stat().st_mtime > sys_bin_exe.stat().st_mtime:
                shutil.copy2(tmp_exe, sys_bin_exe)
        except OSError:
            pass

    for direct_bin in (sys_bin_exe, tmp_exe):
        if direct_bin.exists():
            return str(direct_bin)

    for candidate_name in ("jules.exe", "jules.cmd", "jules"):
        found = shutil.which(candidate_name)
        if found:
            return found

    return None


def resolve_current_git_branch(project_root: Path) -> str:
    """Read the current git branch from `.git/HEAD` without requiring `git` on `PATH`."""
    head_file = project_root / ".git" / "HEAD"
    if head_file.exists():
        content = head_file.read_text(encoding="utf-8").strip()
        if content.startswith("ref: refs/heads/"):
            return content.replace("ref: refs/heads/", "", 1)
        return content[:12]
    return "unknown"


def is_current_branch_pushed_to_origin(project_root: Path) -> bool:
    """
    Check whether the active local branch exists on `origin` (via `.git/refs/remotes/origin/<branch>`
    or `.git/packed-refs`).
    """
    branch = resolve_current_git_branch(project_root)
    if not branch or branch == "unknown":
        return False

    remote_ref = project_root / ".git" / "refs" / "remotes" / "origin" / branch
    if remote_ref.exists():
        return True

    packed_refs = project_root / ".git" / "packed-refs"
    if packed_refs.exists():
        text = packed_refs.read_text(encoding="utf-8", errors="replace")
        if f"refs/remotes/origin/{branch}" in text:
            return True

    return False


def resolve_dispatch_cwd(project_root: Path) -> Path:
    """
    Return `project_root` if the current local branch exists on `origin`.
    If the active local branch has not been pushed to `origin` yet, `jules new` would otherwise
    pass the unpushed branch name (or an empty branch if run outside git) to Google Jules Cloud,
    causing the remote VM to fail at checkout. We prepare a lightweight git context directory
    whose `HEAD` points to `refs/heads/main` so `git branch --show-current` reports `main`
    without switching branches in the user's working tree.
    """
    if is_current_branch_pushed_to_origin(project_root):
        return project_root

    ctx_dir = Path(tempfile.gettempdir()) / "porter_jules_dispatch_ctx"
    git_dir = ctx_dir / ".git"
    refs_heads = git_dir / "refs" / "heads"
    refs_heads.mkdir(parents=True, exist_ok=True)

    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    src_config = project_root / ".git" / "config"
    if src_config.exists():
        shutil.copy2(src_config, git_dir / "config")

    main_ref = project_root / ".git" / "refs" / "remotes" / "origin" / "main"
    if not main_ref.exists():
        main_ref = project_root / ".git" / "refs" / "heads" / "main"
    commit_sha = main_ref.read_text(encoding="utf-8").strip() if main_ref.exists() else ""
    if not commit_sha:
        packed_refs = project_root / ".git" / "packed-refs"
        if packed_refs.exists():
            for line in packed_refs.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.endswith((" refs/remotes/origin/main", " refs/heads/main")):
                    commit_sha = line.split()[0]
                    break
    if not commit_sha:
        commit_sha = "0000000000000000000000000000000000000000"
    (refs_heads / "main").write_text(f"{commit_sha}\n", encoding="utf-8")
    return ctx_dir


def resolve_github_repo(project_root: Path, repo_arg: Optional[str] = None) -> str:
    """
    Dynamically resolve the `<owner>/<repo>` slug from `.git/config` `origin` URL at runtime.
    Zero personal usernames or external repository aliases are hardcoded.
    """
    origin_slug = ""
    git_config = project_root / ".git" / "config"
    if git_config.exists():
        config_text = git_config.read_text(encoding="utf-8", errors="replace")
        match = re.search(
            r"github\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?\s*$",
            config_text,
            re.MULTILINE,
        )
        if match:
            origin_slug = match.group(1)

    if repo_arg:
        cleaned = repo_arg.strip().strip("/")
        if cleaned.startswith("https://github.com/"):
            cleaned = cleaned.replace("https://github.com/", "", 1)
        if cleaned.endswith(".git"):
            cleaned = cleaned[:-4]
        if "/" in cleaned:
            return cleaned
        if origin_slug and "/" in origin_slug:
            owner = origin_slug.split("/", 1)[0]
            return f"{owner}/{cleaned}"
        return cleaned

    if origin_slug:
        return origin_slug

    env_repo = os.environ.get("PORTER_DEFAULT_REPO")
    if env_repo:
        return env_repo

    return project_root.name


def fetch_parsed_jules_sessions() -> Tuple[str, List[JulesSessionRow]]:
    """Query `jules remote list --session` and parse each row into structured `JulesSessionRow` objects."""
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
    if res.returncode != 0 or not res.stdout:
        return "", []

    lines = [line for line in res.stdout.splitlines() if line.strip()]
    if not lines:
        return "", []

    header = lines[0]
    parsed_rows: List[JulesSessionRow] = []
    row_pattern = re.compile(
        r"^\s*(\d+)\s+(.+?)\s+([A-Za-z0-9_.-]+/\S+)\s+(\d+(?:\s+[A-Za-z]+)?(?:\s+ago)?|\S+)\s*(.*)$"
    )
    for raw in lines[1:]:
        m = row_pattern.match(raw)
        if m:
            sid, desc, repo_col, last_act, status_col = (
                m.group(1).strip(),
                m.group(2).strip(),
                m.group(3).strip(),
                m.group(4).strip(),
                m.group(5).strip() or "Completed",
            )
            persona = detect_persona_from_description(desc)
            parsed_rows.append(
                JulesSessionRow(
                    session_id=sid,
                    description=desc,
                    repo=repo_col,
                    last_active=last_act,
                    status=status_col,
                    raw_line=raw,
                    matched_persona=persona,
                )
            )
        else:
            parts = raw.strip().split()
            sid = parts[0] if parts and parts[0].isdigit() else "unknown"
            parsed_rows.append(
                JulesSessionRow(
                    session_id=sid,
                    description=raw.strip(),
                    repo="",
                    last_active="",
                    status="",
                    raw_line=raw,
                    matched_persona=detect_persona_from_description(raw),
                )
            )
    return header, parsed_rows


def repo_matches_filter(row_repo: str, row_raw: str, repo_filter: str) -> bool:
    """
    Match `--repo` filter even when `jules` truncates the Repo column in its table output
    (e.g., `<owner>/Agentic_personal_porter` is truncated to `<owner>/Agentic_perso…`).
    """
    filt = repo_filter.strip().lower()
    if filt in row_raw.lower():
        return True

    cleaned_row_repo = row_repo.lower().rstrip("…").rstrip(".")
    if "/" in filt:
        owner, short = filt.split("/", 1)
    else:
        owner, short = "", filt

    if cleaned_row_repo and "/" in cleaned_row_repo:
        row_owner, row_short = cleaned_row_repo.split("/", 1)
        if owner and owner != row_owner:
            return False
        if short.startswith(row_short) or row_short.startswith(short[:12]):
            return True
    return False


def backup_to_legacy_hr(target_file: Path, project_root: Path) -> Optional[Path]:
    """Create a `.bk` backup of an existing file and archive it into `.legacy_hr/DDMMYYYY/`."""
    if not target_file.exists():
        return None

    day_bucket = datetime.datetime.now().strftime("%d%m%Y")
    legacy_dir = project_root / ".legacy_hr" / day_bucket
    legacy_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = legacy_dir / f"{target_file.name}.{timestamp}.bk"
    shutil.copy2(target_file, backup_path)
    return backup_path


def sync_file_pair(
    project_file: Path,
    system_file: Path,
    direction: str,
    project_root: Path,
) -> str:
    """Synchronize a single file between project and system directories with `.bk` archiving."""
    project_exists = project_file.exists()
    system_exists = system_file.exists()

    if not project_exists and not system_exists:
        return "MISSING_BOTH"

    if project_exists and system_exists:
        proj_bytes = project_file.read_bytes()
        sys_bytes = system_file.read_bytes()
        if proj_bytes == sys_bytes:
            return "IN_SYNC"

        if direction == "project-to-system":
            backup_to_legacy_hr(system_file, project_root)
            system_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(project_file, system_file)
            return "UPDATED_SYSTEM"

        if direction == "system-to-project":
            backup_to_legacy_hr(project_file, project_root)
            project_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(system_file, project_file)
            return "UPDATED_PROJECT"

        proj_mtime = project_file.stat().st_mtime
        sys_mtime = system_file.stat().st_mtime
        if proj_mtime >= sys_mtime:
            backup_to_legacy_hr(system_file, project_root)
            shutil.copy2(project_file, system_file)
            return "SYNCED_PROJ->SYS"
        backup_to_legacy_hr(project_file, project_root)
        shutil.copy2(system_file, project_file)
        return "SYNCED_SYS->PROJ"

    if project_exists and not system_exists:
        if direction in ("both", "project-to-system"):
            system_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(project_file, system_file)
            return "INSTALLED_TO_SYSTEM"
        return "SKIPPED_SYS_MISSING"

    if direction in ("both", "system-to-project"):
        project_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(system_file, project_file)
        return "RESTORED_TO_PROJECT"
    return "SKIPPED_PROJ_MISSING"


def cmd_sync(direction: str) -> int:
    """Synchronize all 12 CLI agent definitions, 8 `.jules` playbooks, and runner modules."""
    project_root = resolve_project_root()
    system_root = resolve_system_config_dir()

    proj_agents_dir = project_root / ".agents" / "agents"
    sys_agents_dir = system_root / "agents"
    proj_jules_dir = project_root / ".jules"
    sys_jules_dir = system_root / "jules"

    proj_agents_dir.mkdir(parents=True, exist_ok=True)
    sys_agents_dir.mkdir(parents=True, exist_ok=True)
    proj_jules_dir.mkdir(parents=True, exist_ok=True)
    sys_jules_dir.mkdir(parents=True, exist_ok=True)

    print(f"🔄 Synchronizing Porter CLI Agents (direction: {direction})")
    print(f"   Active Branch: {resolve_current_git_branch(project_root)}\n")

    print("1. Custom Antigravity CLI Agents (.agents/agents/*.md <-> system agents):")
    for name, spec in PERSONA_ROSTER.items():
        p_file = proj_agents_dir / f"{name}.md"
        s_file = sys_agents_dir / f"{name}.md"
        status = sync_file_pair(p_file, s_file, direction, project_root)
        print(f"   {spec.emoji} {name:<16} -> {status}")

    print("\n2. Jules Operational Playbooks (.jules/*.md <-> system jules):")
    for name, spec in PERSONA_ROSTER.items():
        if not spec.jules_file:
            continue
        p_jules = proj_jules_dir / spec.jules_file
        s_jules = sys_jules_dir / spec.jules_file
        status = sync_file_pair(p_jules, s_jules, direction, project_root)
        print(f"   {spec.emoji} {spec.jules_file:<16} -> {status}")

    for script_name in ("porter_persona_roster.py", "porter_cli_agents.py"):
        src_path = project_root / "scripts" / script_name
        dst_path = sys_agents_dir / script_name
        if src_path.exists() and src_path.resolve() != dst_path.resolve():
            shutil.copy2(src_path, dst_path)

    print("\n✅ Synchronization complete! All 12 personas are ready at project and system levels.")
    return 0


def cmd_list() -> int:
    """
    Display a formatted roster table of all 12 CLI agents, active Git branch,
    and the latest Google Jules Session ID & Status per persona.
    """
    project_root = resolve_project_root()
    system_root = resolve_system_config_dir()
    jules_bin = resolve_jules_executable()
    git_branch = resolve_current_git_branch(project_root)
    branch_pushed = is_current_branch_pushed_to_origin(project_root)
    default_repo = resolve_github_repo(project_root)

    _, all_sessions = fetch_parsed_jules_sessions()
    latest_by_persona: Dict[str, JulesSessionRow] = {}
    for row in all_sessions:
        if row.matched_persona and row.matched_persona not in latest_by_persona:
            if repo_matches_filter(row.repo, row.raw_line, default_repo):
                latest_by_persona[row.matched_persona] = row

    print("========================================================================================================================")
    print("🏛️  AGENTIC PERSONAL PORTER — TRUE CLI & GOOGLE JULES AGENT ROSTER")
    print(
        f"   Branch: {git_branch} ({'pushed' if branch_pushed else 'local-only'}) | "
        f"Jules CLI: {'READY (native binary)' if jules_bin else 'NOT FOUND'}"
    )
    print("========================================================================================================================")
    header = (
        f"{'AGENT':<18} {'CATEGORY':<14} {'PROJ':<6} {'SYS':<6} "
        f"{'PLAYBOOK':<14} {'LATEST JULES SESSION ID':<23} {'JULES STATUS':<18} {'VERIFY TARGET'}"
    )
    print(header)
    print("-" * len(header))

    for name, spec in PERSONA_ROSTER.items():
        proj_ok = (project_root / ".agents" / "agents" / f"{name}.md").exists()
        sys_ok = (system_root / "agents" / f"{name}.md").exists()
        jules_label = spec.jules_file if spec.jules_file else "(constitution)"
        if spec.jules_file:
            jules_exists = (project_root / ".jules" / spec.jules_file).exists() or (
                system_root / "jules" / spec.jules_file
            ).exists()
            jules_status = spec.jules_file if jules_exists else f"!{spec.jules_file}"
        else:
            jules_status = jules_label

        proj_str = "✅" if proj_ok else "❌"
        sys_str = "✅" if sys_ok else "❌"
        latest_row = latest_by_persona.get(name)
        latest_id = latest_row.session_id if latest_row else "-"
        latest_state = f"{latest_row.status} ({latest_row.last_active})" if latest_row else "-"

        print(
            f"{spec.emoji} {name:<15} {spec.category:<14} {proj_str:<5} {sys_str:<5} "
            f"{jules_status:<14} {latest_id:<23} {latest_state[:18]:<18} {spec.make_target}"
        )

    print("========================================================================================================================")
    print("Runbook: documentation/architecture/jules-cli-runbook.md")
    return 0


def run_step(description: str, cmd: Sequence[str], cwd: Path) -> bool:
    """Run a single verification subprocess and stream its output."""
    print(f"   ▶ {description}: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, cwd=str(cwd), check=False)  # nosec B603
        return res.returncode == 0
    except FileNotFoundError as exc:
        print(f"   ❌ Executable not found while running '{cmd[0]}': {exc}")
        return False


def verify_single_persona(agent: str, project_root: Path) -> bool:
    """Execute the automated verification checks for a single persona."""
    py = sys.executable
    spec = PERSONA_ROSTER[agent]
    print(f"\n{spec.emoji} Verifying {spec.title}...")

    if agent == "sentinel":
        return run_step(
            "Sentinel Auth/Security/Mock-Mongo Unit Suite",
            [py, "-m", "pytest", "tests/unit", "-k", "auth or security or mock_mongo", "-v", "--tb=short"],
            project_root,
        )
    if agent == "bolt":
        return run_step(
            "Bolt Database Mock & Performance Suite",
            [py, "-m", "pytest", "tests/unit/test_mock_mongo.py", "-v", "--tb=short"],
            project_root,
        )
    if agent == "palette":
        npm_cmd = "npm.cmd" if sys.platform.startswith("win") else "npm"
        return run_step("Palette Tailwind CSS Build & Asset Validation", [npm_cmd, "run", "build:css"], project_root)
    if agent == "archie":
        ok_ruff = run_step("Archie Modular Ruff Check", [py, "-m", "ruff", "check", "src"], project_root)
        schemas_dir = project_root / "src" / "schemas"
        target_mypy = "src/schemas" if schemas_dir.exists() else "src"
        ok_mypy = run_step("Archie Schema Mypy Check", [py, "-m", "mypy", target_mypy], project_root)
        return ok_ruff and ok_mypy
    if agent == "docdoc":
        return run_step(
            "DocDoc Documentation Governance Check",
            [py, str(project_root / "scripts" / "analyze_scripts" / "verify_doc_hygiene.py")],
            project_root,
        )
    if agent == "dave":
        return run_step(
            "Dave DevOps & CI/CD Security Check",
            [py, str(project_root / "scripts" / "analyze_scripts" / "verify_devops.py")],
            project_root,
        )
    if agent == "crii":
        test_targets = [
            t
            for t in ("tests/unit/test_api_schemas.py", "tests/test_llm_resilience.py", "tests/unit/test_mock_mongo.py")
            if (project_root / t).exists()
        ]
        if not test_targets:
            test_targets = ["tests/unit"]
        return run_step(
            "Crii Adversarial & Resilience Test Suite",
            [py, "-m", "pytest", *test_targets, "-v", "--tb=short"],
            project_root,
        )
    if agent == "jovol":
        return run_step(
            "Jovol JS Functional Component & Spec Kit Check",
            [py, str(project_root / "scripts" / "analyze_scripts" / "verify_components.py")],
            project_root,
        )
    if agent == "silas":
        ok1 = run_step("Silas Gate 1/3 (Ruff)", [py, "-m", "ruff", "check", "src", "tests"], project_root)
        ok2 = run_step("Silas Gate 2/3 (Mypy)", [py, "-m", "mypy", "src"], project_root)
        ok3 = run_step(
            "Silas Gate 3/3 (Pytest Unit Suite)",
            [py, "-m", "pytest", "tests/unit", "-v", "--tb=short"],
            project_root,
        )
        return ok1 and ok2 and ok3

    if spec.partners:
        return all(verify_single_persona(partner, project_root) for partner in spec.partners)
    return True


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
        print(
            f"❌ Error: Unknown persona '{target}'. Valid targets: {', '.join(PERSONA_ROSTER.keys())}, roster, all",
            file=sys.stderr,
        )
        return 1

    results: List[Tuple[str, bool]] = []
    for name in targets:
        passed = verify_single_persona(name, project_root)
        results.append((name, passed))

    print("\n============================================================")
    print("📊 VERIFICATION SUMMARY")
    print("============================================================")
    all_passed = True
    for name, passed in results:
        spec = PERSONA_ROSTER[name]
        badge = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {spec.emoji} {name:<16} : {badge}")
        if not passed:
            all_passed = False

    return 0 if all_passed else 1


def strip_yaml_frontmatter(markdown_text: str) -> str:
    """Remove YAML frontmatter from an agent `.md` file when constructing a Jules session prompt."""
    lines = markdown_text.splitlines()
    if lines and lines[0].strip() == "---":
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                return "\n".join(lines[idx + 1 :]).strip()
    return markdown_text.strip()


def build_composite_prompt(agent: str, task: Optional[str] = None) -> str:
    """
    Assemble the full composite prompt combining:
      1. The 1-line Google Jules persona signature header (so `jules remote list --session` is scannable)
      2. The Assigned Task
      3. The Agent's System Prompt & Core Directives (from `.agents/agents/<agent>.md`)
      4. The Live Operational Playbook (from `.jules/<agent>.md`)
      5. Mandatory Verification Gate instructions
    """
    if agent not in PERSONA_ROSTER:
        raise ValueError(f"Unknown agent '{agent}'. Choose from: {', '.join(PERSONA_ROSTER.keys())}")

    project_root = resolve_project_root()
    system_root = resolve_system_config_dir()
    spec = PERSONA_ROSTER[agent]

    agent_md_path = project_root / ".agents" / "agents" / f"{agent}.md"
    if not agent_md_path.exists():
        agent_md_path = system_root / "agents" / f"{agent}.md"

    first_line = spec.jules_header
    if task:
        first_line = f"{spec.jules_header} | Task: {task}"

    sections: List[str] = [first_line, ""]

    if task:
        sections.append(f"## Assigned Task\n{task}\n")

    if agent_md_path.exists():
        body = strip_yaml_frontmatter(agent_md_path.read_text(encoding="utf-8"))
        sections.append(body)

    if spec.jules_file:
        jules_path = project_root / ".jules" / spec.jules_file
        if not jules_path.exists():
            jules_path = system_root / "jules" / spec.jules_file
        if jules_path.exists():
            sections.append(f"\n## Live Operational Playbook (`.jules/{spec.jules_file}`)\n")
            sections.append(jules_path.read_text(encoding="utf-8").strip())
            sections.append(
                f"\n## Journal Update Requirement\n"
                f"If you discover a new vulnerability, performance bottleneck, or architectural pattern during this session, "
                f"append a concise dated entry (`## YYYY-MM-DD - Title`) to `.jules/{spec.jules_file}`."
            )

    sections.append(
        f"\n## Mandatory Verification Gate\n"
        f"Before completing your session or opening a pull request, run:\n"
        f"```bash\n"
        f"make {spec.make_target}\n"
        f"# or:\n"
        f"uv run python scripts/porter_cli_agents.py verify {agent}\n"
        f"```\n"
        f"Ensure zero regressions and archive any temporary `.bk` backup files into `.legacy_hr/`."
    )

    return "\n".join(sections)


def cmd_prompt(agent: str, task: Optional[str]) -> int:
    """Print the composite prompt for an agent so it can be piped to `jules new` or `agy`."""
    try:
        print(build_composite_prompt(agent, task))
        return 0
    except ValueError as exc:
        print(f"❌ Error: {exc}", file=sys.stderr)
        return 1


def cmd_jules_dispatch(
    agent: str,
    task: Optional[str] = None,
    repo: Optional[str] = None,
    parallel: int = 1,
    dry_run: bool = False,
) -> int:
    """
    Dispatch a persona-aligned coding session to Google Jules CLI (`jules new`)
    by piping the composite persona + `.jules` playbook prompt via stdin.
    """
    if agent not in PERSONA_ROSTER:
        print(f"❌ Error: Unknown agent '{agent}'.", file=sys.stderr)
        return 1

    project_root = resolve_project_root()
    spec = PERSONA_ROSTER[agent]
    effective_task = task.strip() if task and task.strip() else spec.default_task
    resolved_repo = resolve_github_repo(project_root, repo)
    composite_prompt = build_composite_prompt(agent, effective_task)
    jules_bin = resolve_jules_executable()
    dispatch_cwd = resolve_dispatch_cwd(project_root)

    cmd: List[str] = [jules_bin or "jules", "new", "--repo", resolved_repo]
    if parallel > 1:
        cmd.extend(["--parallel", str(parallel)])

    if dry_run:
        print("================================================================================")
        print(f"🧪 [DRY RUN] Google Jules Dispatch Preview for {spec.emoji} {spec.title}")
        print(f"   Repo    : {resolved_repo}")
        print(f"   Parallel: {parallel}")
        print("================================================================================")
        print(composite_prompt)
        return 0

    if not jules_bin:
        print(
            "❌ Error: Google Jules CLI ('jules') not found. Install via `npm install -g @google/jules`.",
            file=sys.stderr,
        )
        return 1

    print(f"🚀 Dispatching {spec.emoji} {spec.title} to Google Jules (repo: {resolved_repo})...")
    res = subprocess.run(  # nosec B603
        cmd,
        input=composite_prompt,
        text=True,
        encoding="utf-8",
        cwd=str(dispatch_cwd),
        check=False,
    )
    return res.returncode


def _dispatch_single_worker(
    agent: str,
    task: Optional[str],
    resolved_repo: str,
    jules_bin: str,
    dispatch_cwd: Path,
) -> Tuple[str, int, str]:
    """Worker function for parallel multi-persona dispatch using direct `jules` binary."""
    spec = PERSONA_ROSTER[agent]
    effective_task = task.strip() if task and task.strip() else spec.default_task
    composite_prompt = build_composite_prompt(agent, effective_task)
    cmd: List[str] = [jules_bin, "new", "--repo", resolved_repo]
    res = subprocess.run(  # nosec B603
        cmd,
        input=composite_prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(dispatch_cwd),
        check=False,
    )
    output = (res.stdout or "") + (f"\n{res.stderr}" if res.stderr else "")
    session_id = "unknown"
    url = ""
    for line in output.splitlines():
        if line.strip().startswith("ID:"):
            session_id = line.split("ID:", 1)[1].strip()
        elif line.strip().startswith("URL:"):
            url = line.split("URL:", 1)[1].strip()
    summary = (
        f"{spec.emoji} {agent:<15} | Status: {'✅ CREATED' if res.returncode == 0 else '❌ FAILED'} "
        f"| ID: {session_id:<20} | {url or output.strip()[:100]}"
    )
    return agent, res.returncode, summary


def cmd_jules_dispatch_batch(
    agents: Sequence[str],
    repo: Optional[str] = None,
    task_override: Optional[str] = None,
    dry_run: bool = False,
) -> int:
    """
    Dispatch multiple personas in parallel to Google Jules CLI using `ThreadPoolExecutor`.
    Accepts explicit persona names or preset groups ('new' -> archie, docdoc, dave, crii, jovol; 'roster' -> all 8).
    """
    expanded: List[str] = []
    for item in agents:
        key = item.lower().strip()
        if key == "new":
            expanded.extend(["archie", "docdoc", "dave", "crii", "jovol"])
        elif key == "roster":
            expanded.extend(["sentinel", "bolt", "palette", "archie", "docdoc", "dave", "crii", "jovol"])
        elif key in PERSONA_ROSTER:
            expanded.append(key)
        else:
            print(
                f"❌ Error: Unknown persona or group '{item}'. Valid: {', '.join(PERSONA_ROSTER.keys())}, new, roster",
                file=sys.stderr,
            )
            return 1

    target_agents = list(dict.fromkeys(expanded))
    project_root = resolve_project_root()
    resolved_repo = resolve_github_repo(project_root, repo)
    dispatch_cwd = resolve_dispatch_cwd(project_root)

    if dry_run:
        print("====================================================================================================")
        print(f"🧪 [DRY RUN] Parallel Batch Dispatch ({len(target_agents)} Personas) -> {resolved_repo}")
        print("====================================================================================================")
        for agent in target_agents:
            spec = PERSONA_ROSTER[agent]
            eff_task = task_override or spec.default_task
            print(f"  • {spec.emoji} {agent:<15} : {eff_task}")
        return 0

    jules_bin = resolve_jules_executable()
    if not jules_bin:
        print("❌ Error: Google Jules CLI ('jules') not found.", file=sys.stderr)
        return 1

    print("====================================================================================================")
    print(f"🚀 PARALLEL GOOGLE JULES DISPATCH — {len(target_agents)} PERSONAS -> {resolved_repo}")
    print("====================================================================================================")
    for agent in target_agents:
        spec = PERSONA_ROSTER[agent]
        print(f"   ▶ Launching {spec.emoji} {spec.title}")

    results_by_agent: Dict[str, Tuple[str, int, str]] = {}
    with ThreadPoolExecutor(max_workers=min(len(target_agents), 6)) as pool:
        future_map = {
            pool.submit(_dispatch_single_worker, agent, task_override, resolved_repo, jules_bin, dispatch_cwd): agent
            for agent in target_agents
        }
        for future in as_completed(future_map):
            agent_name, code, summary = future.result()
            results_by_agent[agent_name] = (agent_name, code, summary)

    print("\n====================================================================================================")
    print("🛰️  PARALLEL DISPATCH RESULTS")
    print("====================================================================================================")
    exit_code = 0
    for agent in target_agents:
        _agent, code, summary = results_by_agent[agent]
        print(f"   {summary}")
        if code != 0:
            exit_code = code
    print("====================================================================================================")
    return exit_code


def cmd_jules_sessions(
    persona: Optional[str] = None,
    repo: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 25,
) -> int:
    """List remote Google Jules sessions with truncation-safe repo filtering and persona tags."""
    header, rows = fetch_parsed_jules_sessions()
    if not rows:
        print("No remote Jules sessions found.")
        return 0

    filtered: List[JulesSessionRow] = []
    for row in rows:
        if persona:
            p_low = persona.lower().strip()
            if (row.matched_persona != p_low) and (p_low not in row.raw_line.lower()):
                continue
        if repo and not repo_matches_filter(row.repo, row.raw_line, repo):
            continue
        if status and status.lower() not in row.status.lower() and status.lower() not in row.raw_line.lower():
            continue
        filtered.append(row)

    print("====================================================================================================================")
    print(
        f"🛰️  GOOGLE JULES REMOTE SESSIONS "
        f"(showing {min(len(filtered), limit)} of {len(filtered)} matching / {len(rows)} total)"
    )
    print("====================================================================================================================")
    print(f"{'PERSONA':<14} {header}")
    print("-" * (len(header) + 15))
    for row in filtered[:limit]:
        if row.matched_persona and row.matched_persona in PERSONA_ROSTER:
            spec = PERSONA_ROSTER[row.matched_persona]
            p_tag = f"{spec.emoji} {row.matched_persona}"
        else:
            p_tag = "🤖 (custom)"
        print(f"{p_tag:<14} {row.raw_line}")
    print("====================================================================================================================")
    return 0


def cmd_jules_repos() -> int:
    """List all GitHub repositories connected to Google Jules CLI."""
    jules_bin = resolve_jules_executable()
    if not jules_bin:
        print("❌ Error: Google Jules CLI ('jules') not found.", file=sys.stderr)
        return 1
    res = subprocess.run([jules_bin, "remote", "list", "--repo"], check=False)  # nosec B603
    return res.returncode


def resolve_session_target(session_or_persona: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve either a numeric Session ID, 'latest', or a persona name ('bolt', 'archie', etc.)
    into `(session_id, matched_persona)`.
    """
    cleaned = session_or_persona.strip()
    project_root = resolve_project_root()
    default_repo = resolve_github_repo(project_root)
    _, rows = fetch_parsed_jules_sessions()

    if cleaned.isdigit():
        for row in rows:
            if row.session_id == cleaned:
                return cleaned, row.matched_persona
        return cleaned, None

    key = cleaned.lower()
    if key == "latest":
        for row in rows:
            if repo_matches_filter(row.repo, row.raw_line, default_repo):
                return row.session_id, row.matched_persona
        if rows:
            return rows[0].session_id, rows[0].matched_persona
        return None, None

    if key in PERSONA_ROSTER:
        for row in rows:
            if (
                row.matched_persona == key
                and repo_matches_filter(row.repo, row.raw_line, default_repo)
                and "failed" not in row.status.lower()
            ):
                return row.session_id, key
        for row in rows:
            if row.matched_persona == key and repo_matches_filter(row.repo, row.raw_line, default_repo):
                return row.session_id, key
        for row in rows:
            if row.matched_persona == key:
                return row.session_id, key
        return None, key

    return None, None


def cmd_jules_pull(session_or_persona: str, apply_patch: bool = False, verify_agent: Optional[str] = None) -> int:
    """Pull a remote Google Jules session diff by Session ID OR by Persona Name."""
    jules_bin = resolve_jules_executable()
    if not jules_bin:
        print("❌ Error: Google Jules CLI ('jules') not found.", file=sys.stderr)
        return 1

    session_id, detected_persona = resolve_session_target(session_or_persona)
    if not session_id:
        print(
            f"❌ Could not find a remote Google Jules session matching '{session_or_persona}'.\n"
            f"   Run `uv run python scripts/porter_cli_agents.py list` to view active Session IDs.",
            file=sys.stderr,
        )
        return 1

    project_root = resolve_project_root()
    cmd = [jules_bin, "remote", "pull", "--session", session_id]
    if apply_patch:
        cmd.append("--apply")

    persona_info = f" (persona: {detected_persona})" if detected_persona else ""
    print(
        f"📥 Pulling Google Jules session {session_id}{persona_info} "
        f"({'with --apply' if apply_patch else 'diff preview only'})..."
    )
    res = subprocess.run(cmd, cwd=str(project_root), check=False)  # nosec B603
    if res.returncode != 0:
        return res.returncode

    effective_verify = verify_agent or (detected_persona if apply_patch and detected_persona in PERSONA_ROSTER else None)
    if effective_verify:
        print(f"\n🔍 Running post-pull verification gate for '{effective_verify}'...")
        return cmd_verify(effective_verify)
    return 0


def cmd_jules_teleport(session_or_persona: str, verify_agent: Optional[str] = None) -> int:
    """Teleport local workspace to a Google Jules session (by ID or persona name) and optionally verify."""
    jules_bin = resolve_jules_executable()
    if not jules_bin:
        print("❌ Error: Google Jules CLI ('jules') not found.", file=sys.stderr)
        return 1

    session_id, detected_persona = resolve_session_target(session_or_persona)
    if not session_id:
        print(
            f"❌ Could not find a remote Google Jules session matching '{session_or_persona}'.\n"
            f"   Run `uv run python scripts/porter_cli_agents.py list` to view active Session IDs.",
            file=sys.stderr,
        )
        return 1

    project_root = resolve_project_root()
    persona_info = f" (persona: {detected_persona})" if detected_persona else ""
    print(f"⚡ Teleporting to Google Jules session {session_id}{persona_info}...")
    res = subprocess.run([jules_bin, "teleport", session_id], cwd=str(project_root), check=False)  # nosec B603
    if res.returncode != 0:
        return res.returncode

    effective_verify = verify_agent or detected_persona
    if effective_verify:
        return cmd_verify(effective_verify)
    return 0


def cmd_run(agent: str, task: str, engine: str, repo: Optional[str] = None, parallel: int = 1) -> int:
    """Dispatch a task to a persona via Antigravity CLI (`agy`), Google `jules` CLI, or stdout."""
    if agent not in PERSONA_ROSTER:
        print(f"❌ Error: Unknown agent '{agent}'.", file=sys.stderr)
        return 1

    if engine == "print":
        return cmd_prompt(agent, task)

    if engine == "jules":
        return cmd_jules_dispatch(agent=agent, task=task, repo=repo, parallel=parallel, dry_run=False)

    if engine == "agy":
        cmd = ["agy", "--agent", agent, task]
        print(f"🚀 Launching Antigravity CLI with agent '{agent}': {' '.join(cmd)}")
        try:
            return subprocess.run(cmd, check=False).returncode  # nosec B603
        except FileNotFoundError:
            print(
                "⚠️  'agy' executable not found on PATH. Printing composite prompt instead:\n",
                file=sys.stderr,
            )
            return cmd_prompt(agent, task)

    print(f"❌ Unknown engine '{engine}'.", file=sys.stderr)
    return 1


def cmd_learn(agent: str, title: str, learning: str, action: str) -> int:
    """Append a dated learning entry to `.jules/<agent>.md` and sync to system config."""
    if agent not in PERSONA_ROSTER or not PERSONA_ROSTER[agent].jules_file:
        print(
            f"❌ Error: Agent '{agent}' does not have a dedicated .jules/*.md playbook.",
            file=sys.stderr,
        )
        return 1

    project_root = resolve_project_root()
    spec = PERSONA_ROSTER[agent]
    jules_path = project_root / ".jules" / str(spec.jules_file)
    backup_to_legacy_hr(jules_path, project_root)

    today = datetime.date.today().isoformat()
    label_key = "Prevention" if agent == "sentinel" else "Action"
    first_key = "Vulnerability" if agent == "sentinel" else "Learning"
    entry = f"\n## {today} - {title}\n**{first_key}:** {learning}\n**{label_key}:** {action}\n"

    with open(jules_path, "a", encoding="utf-8") as handle:
        handle.write(entry)

    print(f"📝 Recorded new learning in {jules_path}")
    return cmd_sync(direction="project-to-system")


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="porter-agent",
        description="True CLI Agent Manager, Google Jules Integrator & Cross-Machine Sync for Agentic Personal Porter",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "list",
        help="List all 12 CLI personas, active branch, and latest remote Session IDs",
    )

    p_sync = sub.add_parser("sync", help="Synchronize CLI agents and .jules playbooks between project and system")
    p_sync.add_argument(
        "--direction",
        choices=["both", "project-to-system", "system-to-project"],
        default="both",
        help="Sync direction (default: both, newest file wins and backups go to .legacy_hr/)",
    )

    p_verify = sub.add_parser("verify", help="Run automated verification gate for a persona, 'roster', or 'all'")
    p_verify.add_argument("target", help="Persona name (e.g. sentinel, bolt, jovol, silas) or 'roster' / 'all'")

    p_prompt = sub.add_parser("prompt", help="Output composite system + .jules prompt for a persona")
    p_prompt.add_argument("agent", choices=list(PERSONA_ROSTER.keys()), help="Target persona name")
    p_prompt.add_argument("--task", default=None, help="Optional task description to append")

    p_run = sub.add_parser("run", help="Run a task with a specific CLI persona via agy, jules, or stdout")
    p_run.add_argument("agent", choices=list(PERSONA_ROSTER.keys()), help="Target persona name")
    p_run.add_argument("task", help="Task instruction for the agent")
    p_run.add_argument(
        "--engine",
        choices=["agy", "jules", "print"],
        default="agy",
        help="Execution engine: 'agy' (Antigravity CLI), 'jules' (Google Jules CLI), or 'print'",
    )
    p_run.add_argument("--repo", default=None, help="Optional GitHub repo (owner/repo) when using --engine jules")
    p_run.add_argument("--parallel", type=int, default=1, help="Number of parallel Jules sessions (1-5)")

    p_jdisp = sub.add_parser(
        "jules-dispatch",
        help="Dispatch a persona + live .jules playbook session directly to Google Jules (`jules new`)",
    )
    p_jdisp.add_argument("agent", choices=list(PERSONA_ROSTER.keys()), help="Target persona to dispatch to Jules")
    p_jdisp.add_argument(
        "task",
        nargs="?",
        default=None,
        help="Optional task instruction (defaults to the persona's built-in constitutional audit task if omitted)",
    )
    p_jdisp.add_argument(
        "--repo",
        default=None,
        help="Target GitHub repo (auto-detected from .git/config if omitted)",
    )
    p_jdisp.add_argument("--parallel", type=int, default=1, help="Parallel Jules sessions to spawn (1-5)")
    p_jdisp.add_argument("--dry-run", action="store_true", help="Preview the full composite prompt without dispatching")

    p_jbatch = sub.add_parser(
        "jules-dispatch-batch",
        help="Dispatch multiple personas in parallel to Google Jules (`docdoc dave crii jovol` or `new`)",
    )
    p_jbatch.add_argument(
        "agents",
        nargs="+",
        help="List of personas to dispatch in parallel, or 'new' (archie docdoc dave crii jovol) / 'roster' (all 8)",
    )
    p_jbatch.add_argument(
        "--repo",
        default=None,
        help="Target GitHub repo (auto-detected from .git/config if omitted)",
    )
    p_jbatch.add_argument("--task", default=None, help="Optional shared task override")
    p_jbatch.add_argument("--dry-run", action="store_true", help="Preview batch dispatch without creating remote sessions")

    p_jsess = sub.add_parser("jules-sessions", help="List and filter remote Google Jules sessions with persona tags")
    p_jsess.add_argument("--persona", default=None, help="Filter sessions by persona (e.g. sentinel, bolt, archie)")
    p_jsess.add_argument("--repo", default=None, help="Filter sessions by repository name (handles truncation)")
    p_jsess.add_argument("--status", default=None, help="Filter sessions by status (e.g. Completed, Awaiting, Planning)")
    p_jsess.add_argument("--limit", type=int, default=25, help="Max sessions to display (default: 25)")

    sub.add_parser("jules-repos", help="List GitHub repositories connected to your Google Jules account")

    p_jpull = sub.add_parser(
        "jules-pull",
        help="Pull a remote Google Jules session diff by Session ID OR by Persona Name (e.g. `bolt` or `latest`)",
    )
    p_jpull.add_argument(
        "session_id",
        help="The Google Jules Session ID, persona name (e.g. bolt, archie), or 'latest'",
    )
    p_jpull.add_argument("--apply", action="store_true", help="Apply the pulled patch to the local repository")
    p_jpull.add_argument(
        "--verify",
        choices=list(PERSONA_ROSTER.keys()) + ["roster", "all"],
        default=None,
        help="Run the specified persona verification gate immediately after pulling",
    )

    p_jtele = sub.add_parser(
        "jules-teleport",
        help="Teleport to a Google Jules session by Session ID OR Persona Name and optionally verify",
    )
    p_jtele.add_argument(
        "session_id",
        help="The Google Jules Session ID, persona name (e.g. bolt, archie), or 'latest'",
    )
    p_jtele.add_argument(
        "--verify",
        choices=list(PERSONA_ROSTER.keys()) + ["roster", "all"],
        default=None,
        help="Run the specified persona verification gate after teleporting",
    )

    p_learn = sub.add_parser("learn", help="Append a new learning to .jules/<agent>.md and sync globally")
    p_learn.add_argument("agent", choices=[k for k, v in PERSONA_ROSTER.items() if v.jules_file], help="Jules persona")
    p_learn.add_argument("--title", required=True, help="Short title for the learning")
    p_learn.add_argument("--learning", required=True, help="What was learned or what vulnerability was found")
    p_learn.add_argument("--action", required=True, help="Actionable rule or prevention measure")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "list":
        return cmd_list()
    if args.command == "sync":
        return cmd_sync(direction=args.direction)
    if args.command == "verify":
        return cmd_verify(target=args.target)
    if args.command == "prompt":
        return cmd_prompt(agent=args.agent, task=args.task)
    if args.command == "run":
        return cmd_run(agent=args.agent, task=args.task, engine=args.engine, repo=args.repo, parallel=args.parallel)
    if args.command == "jules-dispatch":
        return cmd_jules_dispatch(
            agent=args.agent,
            task=args.task,
            repo=args.repo,
            parallel=args.parallel,
            dry_run=args.dry_run,
        )
    if args.command == "jules-dispatch-batch":
        return cmd_jules_dispatch_batch(
            agents=args.agents,
            repo=args.repo,
            task_override=args.task,
            dry_run=args.dry_run,
        )
    if args.command == "jules-sessions":
        return cmd_jules_sessions(
            persona=args.persona,
            repo=args.repo,
            status=args.status,
            limit=args.limit,
        )
    if args.command == "jules-repos":
        return cmd_jules_repos()
    if args.command == "jules-pull":
        return cmd_jules_pull(session_or_persona=args.session_id, apply_patch=args.apply, verify_agent=args.verify)
    if args.command == "jules-teleport":
        return cmd_jules_teleport(session_or_persona=args.session_id, verify_agent=args.verify)
    if args.command == "learn":
        return cmd_learn(agent=args.agent, title=args.title, learning=args.learning, action=args.action)
    return 0


if __name__ == "__main__":
    sys.exit(main())
