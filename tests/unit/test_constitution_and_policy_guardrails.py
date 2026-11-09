"""Unit tests for Notes_repo Policy Synchronization & Company Constitution Leak Guardrails."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "analyze_scripts"))

import git_hooks_runner  # noqa: E402
import verify_doc_hygiene  # noqa: E402


@pytest.mark.unit
def test_repository_passes_all_docdoc_skill_and_constitution_gates() -> None:
    """Verify the active repository passes all 6 DocDoc, Skill, and Constitution Leak gates."""
    assert verify_doc_hygiene.check_root_markdown(REPO_ROOT) == []
    assert verify_doc_hygiene.check_documentation_naming(REPO_ROOT) == []
    assert verify_doc_hygiene.check_no_absolute_paths(REPO_ROOT) == []
    assert verify_doc_hygiene.check_dangling_backups(REPO_ROOT) == []
    assert verify_doc_hygiene.check_skill_hygiene(REPO_ROOT) == []
    assert verify_doc_hygiene.check_constitution_and_discrete_leaks(REPO_ROOT) == []


@pytest.mark.unit
def test_constitution_leak_detector_blocks_level0_markers(tmp_path: Path) -> None:
    """Verify check_constitution_and_discrete_leaks catches missing .gitignore and Level-0 leaks."""
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True)
    # Missing .gitignore entry should fail
    errs_missing = verify_doc_hygiene.check_constitution_and_discrete_leaks(tmp_path)
    assert any(".organization_discrete" in e for e in errs_missing)

    # Add .gitignore with .organization_discrete, then track a leaked file
    (tmp_path / ".gitignore").write_text(
        "documentation/.organization_discrete/\n", encoding="utf-8"
    )
    leaked_doc = tmp_path / "documentation" / "leaked-spec.md"
    leaked_doc.parent.mkdir(parents=True, exist_ok=True)
    leaked_doc.write_text("# Spec\nCopied from Nexus_Constitution.md directly.\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", ".gitignore", "documentation/leaked-spec.md"], cwd=str(tmp_path), check=True
    )

    errs_leaked = verify_doc_hygiene.check_constitution_and_discrete_leaks(tmp_path)
    assert any("Level-0 Company Constitution marker leaked" in e for e in errs_leaked)


@pytest.mark.unit
def test_branch_and_35_file_stacked_pr_guardrail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify 3-Tier Git Flow blocks direct commits on main and > 35 staged files."""
    monkeypatch.delenv("ALLOW_MAIN_COMMIT", raising=False)
    monkeypatch.delenv("ALLOW_LARGE_PR", raising=False)

    def fake_run_cmd(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        if "rev-parse" in args:
            return subprocess.CompletedProcess(args, 0, stdout="main\n", stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(git_hooks_runner, "_run_cmd", fake_run_cmd)
    errs = git_hooks_runner.check_branch_and_pr_size(tmp_path, staged_count=40)
    assert any("Direct commits to 'main' blocked" in e for e in errs)
    assert any("Staged commit modifies 40 files (max <= 35)" in e for e in errs)
