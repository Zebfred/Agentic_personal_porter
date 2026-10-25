"""
Google Jules Work Order Formatter & Dispatcher (`@google/jules` Bridge).

Formats standardized Jira tickets and Spec-Kit tasks into self-contained
`JulesWorkOrder` packages complete with:
- Issue summary, task ID (`T001`+), and specification acceptance criteria
- Target file paths
- Assigned `.jules/<persona>.md` operational playbook rules
- Mandatory verification gate commands (`make test-<persona>` + `make verify-done`)

Executes `@google/jules` (`jules new ...`) strictly with `shell=False` (Sentinel).
"""

import os
import re
import shutil
import subprocess  # nosec B404
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.database.mongo_client.uuid_manager import UUIDGenerator
from src.integrations.jira_client import JiraClient
from src.schemas.jira_models import JiraIssueRecord, JulesWorkOrder, PersonaType
from src.utils.path_utils import get_project_root

logger = logging.getLogger(__name__)

SESSION_ID_REGEX = re.compile(r"\b(jules-[a-zA-Z0-9_-]+)\b", re.IGNORECASE)

PERSONA_PLAYBOOK_MAP: dict[PersonaType, tuple[str, str]] = {
    "sentinel": (".jules/sentinel.md", "make test-sentinel"),
    "bolt": (".jules/bolt.md", "make test-bolt"),
    "palette": (".jules/palette.md", "make test-palette"),
    "archie": (".jules/archie.md", "make test-archie"),
    "docdoc": (".jules/docdoc.md", "make test-docdoc"),
    "dave": (".jules/dave.md", "make test-dave"),
    "crii": (".jules/crii.md", "make test-crii"),
    "jovol": (".jules/jovol.md", "make test-jovol"),
    "silas": (".agents/rules/silas_protocol.md", "make test-silas"),
}


class JulesDispatchError(Exception):
    """Raised when a ticket fails pre-dispatch validation or Jules CLI execution fails."""


class JulesDispatcher:
    """
    Transforms standardized `JiraIssueRecord` instances into `JulesWorkOrder`
    packages and dispatches them to Google Jules CLI (`@google/jules`).
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root = project_root or get_project_root()

    @staticmethod
    def _resolve_jules_binary() -> str:
        """
        Resolve the `jules` CLI binary. Prefers `"jules"` on PATH, and falls back
        to `~/.nvm/versions/node/*/bin/jules` in non-interactive shells if needed.
        """
        if shutil.which("jules"):
            return "jules"
        nvm_candidates = sorted(
            Path.home().glob(".nvm/versions/node/*/bin/jules"),
            reverse=True,
        )
        if nvm_candidates and nvm_candidates[0].is_file():
            return str(nvm_candidates[0])
        return "jules"

    def _load_persona_playbook_excerpt(
        self,
        playbook_rel_path: str,
        persona: PersonaType,
    ) -> str:
        """
        Read the persona's operational playbook from `.jules/<persona>.md` and
        combine with its static definition in `.agents/agents/<persona>.md`.
        """
        sections: list[str] = []
        agent_path = self.project_root / f".agents/agents/{persona}.md"
        if agent_path.exists():
            sections.append(agent_path.read_text(encoding="utf-8").strip()[:2000])

        full_path = self.project_root / playbook_rel_path
        if full_path.exists():
            sections.append(full_path.read_text(encoding="utf-8").strip()[:2500])

        if not sections:
            return f"Follow persona rules defined in {playbook_rel_path}."
        return "\n\n".join(sections)[:4500]

    def _record_jules_activity(self, work_order: JulesWorkOrder) -> None:
        """Append a structured dispatch telemetry line to `.jules/activity.log`."""
        try:
            jules_dir = self.project_root / ".jules"
            jules_dir.mkdir(parents=True, exist_ok=True)
            log_file = jules_dir / "activity.log"
            ts = datetime.now(timezone.utc).isoformat()
            line = (
                f"[{ts}] status={work_order.dispatch_status} "
                f"persona={work_order.persona} task={work_order.task_id or 'N/A'} "
                f"jira={work_order.jira_key} session={work_order.jules_session_id or 'preview'} "
                f"corr={work_order.correlation_id}\n"
            )
            with log_file.open("a", encoding="utf-8") as fh:
                fh.write(line)
        except Exception as exc:
            logger.debug("Could not write to .jules/activity.log: %s", exc)

    @staticmethod
    def _format_work_order_prompt(
        issue: JiraIssueRecord,
        feature_id: str,
        persona: PersonaType,
        playbook_rel_path: str,
        paths_formatted: str,
        playbook_excerpt: str,
        verification_commands: list[str],
    ) -> str:
        """Assemble the structured Markdown prompt for a Google Jules work order."""
        prompt_lines = [
            f"# Jules Work Order: [{issue.jira_key}] {issue.summary}",
            f"- **Feature**: `{feature_id}`",
            f"- **Spec-Kit Task ID**: `{issue.task_id or 'N/A'}`",
            f"- **Assigned Persona**: `{persona}` (`{playbook_rel_path}`)",
            f"- **Target Files**: `{paths_formatted}`",
            f"- **Correlation ID**: `{issue.correlation_id}`",
            "",
            "## Task Specification & Acceptance Criteria",
            issue.description.strip() or issue.summary,
            "",
            f"## Operational Playbook Rules ({playbook_rel_path})",
            playbook_excerpt,
            "",
            "## Mandatory Definition-of-Done Verification Gates",
            "Before completing this session or opening a PR, all of the following commands MUST exit 0:",
            *[f"- `{cmd}`" for cmd in verification_commands],
        ]
        return "\n".join(prompt_lines)[:30000]

    def build_work_order(
        self,
        issue: JiraIssueRecord,
        target_paths: Optional[list[str]] = None,
        persona_override: Optional[PersonaType] = None,
        dry_run: bool = True,
    ) -> JulesWorkOrder:
        """Validate a `JiraIssueRecord` and assemble a complete `JulesWorkOrder`."""
        if not issue.description.strip() and not issue.task_id:
            raise JulesDispatchError(
                f"Issue {issue.jira_key} is missing required specification context "
                "(requires a non-empty description or linked Spec-Kit task_id)."
            )

        persona: PersonaType = persona_override or issue.persona or "silas"
        playbook_rel_path, persona_test_cmd = PERSONA_PLAYBOOK_MAP.get(
            persona, (".agents/rules/silas_protocol.md", "make test-silas")
        )
        verification_commands = [persona_test_cmd, "make verify-done"]
        playbook_excerpt = self._load_persona_playbook_excerpt(playbook_rel_path, persona)
        paths_list = target_paths or []
        paths_formatted = ", ".join(paths_list) if paths_list else "See task description"
        feature_id = issue.feature_id or "002-jira-jules-bridge"
        formatted_prompt = self._format_work_order_prompt(
            issue,
            feature_id,
            persona,
            playbook_rel_path,
            paths_formatted,
            playbook_excerpt,
            verification_commands,
        )
        work_order_id = UUIDGenerator.generate_for_jira_issue(
            f"workorder::{issue.jira_key}::{issue.task_id or 'none'}",
            issue.user_email,
        )
        return JulesWorkOrder(
            work_order_id=work_order_id,
            user_email=issue.user_email,
            jira_key=issue.jira_key,
            task_id=issue.task_id,
            feature_id=feature_id,
            persona=persona,
            playbook_path=playbook_rel_path,
            target_paths=paths_list,
            verification_commands=verification_commands,
            formatted_prompt=formatted_prompt,
            dry_run=dry_run,
            dispatch_status="preview" if dry_run else "queued",
            correlation_id=issue.correlation_id,
        )

    @staticmethod
    def _annotate_jira_issue(
        jira_client: Optional[JiraClient],
        work_order: JulesWorkOrder,
        session_id: str,
    ) -> None:
        """Annotate a non-local Jira issue with the dispatched Jules session metadata."""
        if jira_client is None or work_order.jira_key.startswith("LOCAL-"):
            return
        comment_body = (
            f"🚀 Dispatched to Google Jules asynchronous coding agent.\n"
            f"- Session Reference: {session_id}\n"
            f"- Persona Playbook: {work_order.playbook_path}\n"
            f"- Verification Gates: {', '.join(work_order.verification_commands)}\n"
            f"- Correlation ID: {work_order.correlation_id}"
        )
        try:
            jira_client.add_comment(work_order.jira_key, comment_body)
        except Exception as exc:
            logger.warning(
                "Unable to annotate Jira ticket %s after Jules dispatch: %s",
                work_order.jira_key,
                exc,
            )

    def dispatch_work_order(
        self,
        work_order: JulesWorkOrder,
        jira_client: Optional[JiraClient] = None,
    ) -> JulesWorkOrder:
        """
        Execute a `JulesWorkOrder` via `@google/jules` CLI (`jules new ...`)
        when `dry_run=False`, log activity to `.jules/activity.log`, and annotate
        the linked Jira issue with the session ID.
        """
        if work_order.dry_run:
            preview_order = work_order.model_copy(update={"dispatch_status": "preview"})
            self._record_jules_activity(preview_order)
            return preview_order

        jules_bin = self._resolve_jules_binary()
        subproc_env = os.environ.copy()
        if jules_bin != "jules":
            bin_dir = str(Path(jules_bin).parent)
            subproc_env["PATH"] = f"{bin_dir}:{subproc_env.get('PATH', '')}"

        try:
            proc = subprocess.run(  # nosec B603
                [jules_bin, "new", work_order.formatted_prompt],
                capture_output=True,
                text=True,
                shell=False,
                timeout=30,
                check=False,
                env=subproc_env,
            )
        except FileNotFoundError as exc:
            raise JulesDispatchError(
                "Google Jules CLI ('jules') is not installed or not on PATH. "
                "Install via `npm install -g @google/jules` or use `--dry-run`."
            ) from exc

        if proc.returncode != 0:
            err_msg = (proc.stderr or proc.stdout or "Unknown Jules CLI error").strip()
            raise JulesDispatchError(f"Jules CLI dispatch failed: {err_msg}")

        stdout_text = (proc.stdout or "").strip()
        match = SESSION_ID_REGEX.search(stdout_text)
        session_id = match.group(1) if match else f"jules-{work_order.work_order_id[:8]}"

        updated = work_order.model_copy(
            update={
                "dispatch_status": "dispatched",
                "jules_session_id": session_id,
            }
        )
        self._record_jules_activity(updated)
        self._annotate_jira_issue(jira_client, work_order, session_id)
        return updated
