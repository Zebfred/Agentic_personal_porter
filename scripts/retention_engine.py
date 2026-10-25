#!/usr/bin/env python3
"""4-Tier Retention & Dynamic .geminiignore Engine (retention_engine.py).

Implements the Nexus LLC 4-Tier Date & Compression Lifecycle for `.legacy_hr/`
and `.logs/` (`DDMMYYYY/` -> `MMYYYY/` -> `YYYY_{PROJECT_NAME}/` -> `.tar.gz`)
while keeping scripts < 200 lines and functions < 60 lines.
"""

# fmt: off
from __future__ import annotations

import datetime
import os
import re
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

DDMMYYYY_RE = re.compile(r"^(?P<dd>\d{2})(?P<mm>\d{2})(?P<yyyy>\d{4})$")
MMYYYY_RE = re.compile(r"^(?P<mm>\d{2})(?P<yyyy>\d{4})$")
YYYY_PROJ_RE = re.compile(r"^(?P<yyyy>\d{4})_(?P<proj>.+)$")
BEGIN_MARKER = "# BEGIN AUTO-MANAGED LOGS RETENTION (scripts/log_run.py)"
END_MARKER = "# END AUTO-MANAGED LOGS RETENTION (scripts/log_run.py)"


def resolve_repo_root(explicit_root: Optional[str] = None) -> Path:
    """Resolve the repository root directory from explicit argument, script path, or CWD."""
    if explicit_root:
        return Path(explicit_root).expanduser().resolve()
    script_dir = Path(__file__).resolve().parent
    return script_dir.parent if script_dir.name == "scripts" else Path.cwd().resolve()


def sanitize_project_name(repo_root: Path) -> str:
    """Return a clean filesystem-safe project name for YYYY_{PROJECT_NAME} archives."""
    return re.sub(r"[^A-Za-z0-9_\-]", "_", repo_root.name.strip()) or "Project"


def get_daily_dir(base_dir: Path, now: Optional[datetime.datetime] = None) -> Path:
    """Return and create today's `DDMMYYYY` directory inside `base_dir`."""
    daily_path = base_dir / (now or datetime.datetime.now()).strftime("%d%m%Y")
    daily_path.mkdir(parents=True, exist_ok=True)
    return daily_path


def _move_directory_contents(src_dir: Path, dst_dir: Path) -> None:
    """Merge all files and subdirectories from `src_dir` into `dst_dir` without overwriting."""
    dst_dir.mkdir(parents=True, exist_ok=True)
    for item in list(src_dir.iterdir()):
        target = dst_dir / item.name
        if item.is_dir() and target.exists() and target.is_dir():
            _move_directory_contents(item, target)
        else:
            if not item.is_dir() and target.exists():
                target = dst_dir / f"{item.stem}.{datetime.datetime.now().strftime('%H%M%S')}{item.suffix}"
            shutil.move(str(item), str(target))
    shutil.rmtree(src_dir, ignore_errors=True)


def _compress_yearly_dir(yearly_dir: Path, base_dir: Path) -> Path:
    """Compress `YYYY_{PROJECT_NAME}/` into `YYYY_{PROJECT_NAME}.tar.gz`, merging if archive exists."""
    archive_path = base_dir / f"{yearly_dir.name}.tar.gz"
    with tempfile.TemporaryDirectory(prefix="nexus_archive_") as tmp_str:
        tmp_path = Path(tmp_str)
        staging = tmp_path / yearly_dir.name
        staging.mkdir(parents=True, exist_ok=True)
        if archive_path.exists() and tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path, "r:gz") as old_tar:
                for m in old_tar.getmembers():
                    if not m.name.startswith("/") and ".." not in m.name.split("/"):
                        old_tar.extract(m, path=tmp_path)  # noqa: S202
        _move_directory_contents(yearly_dir, staging)
        tmp_archive = base_dir / f".{yearly_dir.name}.tar.gz.tmp"
        with tarfile.open(tmp_archive, "w:gz") as new_tar:
            new_tar.add(staging, arcname=yearly_dir.name)
        shutil.move(str(tmp_archive), str(archive_path))
    shutil.rmtree(yearly_dir, ignore_errors=True)
    return archive_path


def _stage1_organize_loose(base_dir: Path, dt: datetime.datetime) -> List[str]:
    """Move loose files or legacy subfolders into `DDMMYYYY/` or `MMYYYY/` based on mtime."""
    moved: List[str] = []
    for entry in list(base_dir.iterdir()):
        name = entry.name
        if name.endswith(".tar.gz") or name.startswith(".") or DDMMYYYY_RE.match(name) or MMYYYY_RE.match(name) or YYYY_PROJ_RE.match(name):
            continue
        mtime = datetime.datetime.fromtimestamp(entry.stat().st_mtime) if entry.exists() else dt
        dest = base_dir / (mtime.strftime("%m%Y") if (mtime.year, mtime.month) < (dt.year, dt.month) else mtime.strftime("%d%m%Y"))
        dest.mkdir(parents=True, exist_ok=True)
        if entry.is_dir():
            _move_directory_contents(entry, dest / name)
        else:
            target = dest / (f"{entry.stem}.{dt.strftime('%H%M%S')}{entry.suffix}" if (dest / name).exists() else name)
            shutil.move(str(entry), str(target))
        moved.append(f"{name} -> {dest.name}/")
    return moved


def rotate_tiered_directory(base_dir: Path, project_name: str, now: Optional[datetime.datetime] = None) -> Dict[str, List[str]]:
    """Execute the 4-stage Nexus retention lifecycle inside `base_dir` (`.legacy_hr` or `.logs`)."""
    dt = now or datetime.datetime.now()
    base_dir.mkdir(parents=True, exist_ok=True)
    report: Dict[str, List[str]] = {
        "organized_to_daily_or_monthly": _stage1_organize_loose(base_dir, dt),
        "rolled_to_monthly": [],
        "rolled_to_yearly": [],
        "compressed_to_targz": [],
    }
    for entry in [e for e in base_dir.iterdir() if e.is_dir()]:
        m_d = DDMMYYYY_RE.match(entry.name)
        if m_d and (int(m_d.group("yyyy")), int(m_d.group("mm"))) < (dt.year, dt.month):
            mon = base_dir / f"{int(m_d.group('mm')):02d}{int(m_d.group('yyyy')):04d}"
            _move_directory_contents(entry, mon)
            report["rolled_to_monthly"].append(f"{entry.name}/ -> {mon.name}/")

    for entry in [e for e in base_dir.iterdir() if e.is_dir()]:
        m_m = MMYYYY_RE.match(entry.name)
        if m_m and (int(m_m.group("yyyy")) < dt.year or ((dt.year - int(m_m.group("yyyy"))) * 12 + (dt.month - int(m_m.group("mm")))) >= 12):
            yr = base_dir / f"{int(m_m.group('yyyy')):04d}_{project_name}"
            _move_directory_contents(entry, yr / entry.name)
            report["rolled_to_yearly"].append(f"{entry.name}/ -> {yr.name}/{entry.name}/")

    root_dirs = {p.name for p in base_dir.iterdir() if p.is_dir()}
    for entry in [e for e in base_dir.iterdir() if e.is_dir() and YYYY_PROJ_RE.match(e.name)]:
        yyyy_str = entry.name.split("_", 1)[0]
        next_jan = f"01{int(yyyy_str) + 1:04d}"
        inside = {p.name for p in entry.iterdir()}
        has_dec = f"12{yyyy_str}" in inside or any(n.endswith(f"12{yyyy_str}") for n in inside)
        has_jan = next_jan in inside or next_jan in root_dirs or any(n.endswith(next_jan) for n in root_dirs)
        if (has_dec or has_jan or (dt.year > int(yyyy_str) and inside)) and inside:
            report["compressed_to_targz"].append(_compress_yearly_dir(entry, base_dir).name)
    return report


def sync_geminiignore_log_rules(repo_root: Path, now: Optional[datetime.datetime] = None) -> List[str]:
    """Keep recent logs (<= 3 months) visible in `.geminiignore` while ignoring >3m and year folders."""
    dt = now or datetime.datetime.now()
    geminiignore, logs_dir = repo_root / ".geminiignore", repo_root / ".logs"
    rules: List[str] = [".logs/*_*/", ".logs/*.tar.gz"]
    if logs_dir.exists():
        for entry in sorted((e for e in logs_dir.iterdir() if e.is_dir()), key=lambda p: p.name):
            m_m = MMYYYY_RE.match(entry.name)
            if m_m and ((dt.year - int(m_m.group("yyyy"))) * 12 + (dt.month - int(m_m.group("mm")))) > 3:
                rules.append(f".logs/{entry.name}/")
    block = "\n".join([BEGIN_MARKER, "# Recent logs (<= 3 months) remain visible to Gemini", *rules, END_MARKER])
    existing = geminiignore.read_text(encoding="utf-8", errors="replace") if geminiignore.exists() else ""
    cleaned, in_blk = [], False
    for line in existing.splitlines():
        s = line.strip()
        in_blk = True if s == BEGIN_MARKER else (False if s == END_MARKER else in_blk)
        if not in_blk and s not in {BEGIN_MARKER, END_MARKER, ".logs/", ".logs"}:
            cleaned.append(line)
    base = "\n".join(cleaned).rstrip()
    updated = f"{base}\n\n{block}\n" if base else f"{block}\n"
    if updated != existing:
        geminiignore.write_text(updated, encoding="utf-8")
    return rules


def archive_backup_file(target_file: Path, repo_root: Path, copy_only: bool = True, now: Optional[datetime.datetime] = None) -> Optional[Path]:
    """Place a `.bk` backup of `target_file` inside `.legacy_hr/DDMMYYYY/` and run tiered rotation."""
    if not target_file.exists() or not target_file.is_file():
        return None
    dt = now or datetime.datetime.now()
    try:
        rel = target_file.resolve().relative_to(repo_root.resolve())
        if rel.parts and rel.parts[0] in {".legacy_hr", ".logs"}:
            return None
        safe_rel = "__".join(rel.parts)
    except ValueError:
        safe_rel = target_file.name
    ts = dt.strftime("%H%M%S")
    suffix = f".{ts}" if (safe_rel.endswith(".bk") or ".bk." in safe_rel) else f".{ts}.bk"
    backup_path = get_daily_dir(repo_root / ".legacy_hr", now=dt) / f"{safe_rel}{suffix}"
    shutil.copy2(target_file, backup_path) if copy_only else shutil.move(str(target_file), str(backup_path))
    rotate_tiered_directory(repo_root / ".legacy_hr", sanitize_project_name(repo_root), now=dt)
    sync_geminiignore_log_rules(repo_root, now=dt)
    return backup_path


def sweep_stray_backups_to_daily(repo_root: Path, now: Optional[datetime.datetime] = None) -> int:
    """Move any stray `*.bk*` files outside `.legacy_hr/` into `.legacy_hr/DDMMYYYY/` and rotate."""
    if not repo_root.exists():
        return 0
    dt, moved = now or datetime.datetime.now(), 0
    ignored = {".git", ".legacy_hr", ".logs", ".venv", "venv", "node_modules", "__pycache__"}
    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in ignored]
        for file in [f for f in files if f.endswith(".bk") or ".bk." in f or re.search(r"\.bk\d*$", f)]:
            shutil.move(str(Path(root) / file), str(get_daily_dir(repo_root / ".legacy_hr", now=dt) / f"{file}.{dt.strftime('%H%M%S')}"))
            moved += 1
    rotate_tiered_directory(repo_root / ".legacy_hr", sanitize_project_name(repo_root), now=dt)
    sync_geminiignore_log_rules(repo_root, now=dt)
    return moved
