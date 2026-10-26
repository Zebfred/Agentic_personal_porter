#!/usr/bin/env python3
"""
Environment, Git Branch, NVM/Binary Resolution & `.jules/activity.log` Helpers (< 200 lines).
"""

from __future__ import annotations

import datetime
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from typing import Optional


def resolve_project_root() -> Path:
    """Locate the repository root from script location or current working directory."""
    script_path = Path(__file__).resolve()
    for parent in script_path.parents:
        if (parent / ".jules").exists() and (parent / "Makefile").exists():
            return parent
    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / ".jules").exists() and (candidate / "Makefile").exists():
            return candidate
    return script_path.parents[2]


def resolve_system_config_dir() -> Path:
    """Return the global CLI configuration directory from `PORTER_SYSTEM_CONFIG_DIR` or `~/.gemini/config`."""
    env_dir = os.environ.get("PORTER_SYSTEM_CONFIG_DIR")
    if env_dir:
        return Path(env_dir).expanduser()
    return Path.home() / ".gemini" / "config"


def resolve_jules_executable() -> Optional[str]:
    """
    Locate the `jules` binary across `PORTER_JULES_BIN`, cached config bin, `PATH`, and `~/.nvm`.
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

    nvm_dir = Path.home() / ".nvm" / "versions" / "node"
    if nvm_dir.exists():
        for candidate in sorted(nvm_dir.glob("*/bin/jules"), reverse=True):
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
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
    """Check whether the active local branch exists on `origin`."""
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
    """Return `project_root` if pushed to `origin`, else a lightweight `main` git context."""
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
    commit_sha = commit_sha or ("0" * 40)
    (refs_heads / "main").write_text(f"{commit_sha}\n", encoding="utf-8")
    return ctx_dir


def resolve_github_repo(project_root: Path, repo_arg: Optional[str] = None) -> str:
    """Dynamically resolve the `<owner>/<repo>` slug from `.git/config` `origin` URL at runtime."""
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
            return f"{origin_slug.split('/', 1)[0]}/{cleaned}"
        return cleaned

    return origin_slug or os.environ.get("PORTER_DEFAULT_REPO") or project_root.name


def log_jules_activity(project_root: Path, action: str, persona: str, details: str) -> None:
    """Append an operational trace line to `.jules/activity.log`."""
    try:
        log_path = project_root / ".jules" / "activity.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(f"[{ts}] action={action} persona={persona} {details}\n")
    except OSError:
        pass
