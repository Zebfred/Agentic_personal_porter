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
import re
import subprocess
import logging
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
    "silas": (".agent/rules/silas_protocol.md", "make test-silas"),
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

    def _load_persona_playbook_excerpt(self, playbook_rel_path: str) -> str:
        """Read the persona's operational playbook from `.jules/<persona>.md`."""
        full_path = self.project_root / playbook_rel_path
        if not full_path.exists():
            return f"Follow persona rules defined in {playbook_rel_path}."
        content = full_path.read_text(encoding="utf-8").strip()
        return content[:4000]

    def build_work_order(
        self,
        issue: JiraIssueRecord,
        target_paths: Optional[list[str]] = None,
        persona_override: Optional[PersonaType] = None,
        dry_run: bool = True,
    ) -> JulesWorkOrder:
        """
        Validate a `JiraIssueRecord` and assemble a complete `JulesWorkOrder`
        containing the specification context, `.jules/<persona>.md` rules, and
        mandatory verification gates.
        """
        if not issue.description.strip() and not issue.task_id:
            raise JulesDispatchError(
                f"Issue {issue.jira_key} is missing required specification context "
                "(requires a non-empty description or linked Spec-Kit task_id)."
            )

        persona: PersonaType = persona_override or issue.persona or "silas"
        playbook_rel_path, persona_test_cmd = PERSONA_PLAYBOOK_MAP.get(
            persona,
            (".agent/rules/silas_protocol.md", "make test-silas"),
        )
        verification_commands = [persona_test_cmd, "make verify-done"]
        playbook_excerpt = self._load_persona_playbook_excerpt(playbook_rel_path)
        paths_list = target_paths or []
        paths_formatted = (
            ", ".join(paths_list) if paths_list else "See task description"
        )
        feature_id = issue.feature_id or "002-jira-jules-bridge"

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
        formatted_prompt = "\n".join(prompt_lines)[:30000]

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

    def dispatch_work_order(
        self,
        work_order: JulesWorkOrder,
        jira_client: Optional[JiraClient] = None,
    ) -> JulesWorkOrder:
        """
        Execute a `JulesWorkOrder` via `@google/jules` CLI (`jules new ...`)
        when `dry_run=False`, and annotate the linked Jira issue with the session ID.
        """
        if work_order.dry_run:
            return work_order.model_copy(update={"dispatch_status": "preview"})

        try:
            proc = subprocess.run(
                ["jules", "new", work_order.formatted_prompt],
                capture_output=True,
                text=True,
                shell=False,
                timeout=30,
                check=False,
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
        session_id = (
            match.group(1)
            if match
            else f"jules-{work_order.work_order_id[:8]}"
        )

        updated = work_order.model_copy(
            update={
                "dispatch_status": "dispatched",
                "jules_session_id": session_id,
            }
        )

        if jira_client is not None and not work_order.jira_key.startswith("LOCAL-"):
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

        return updated
