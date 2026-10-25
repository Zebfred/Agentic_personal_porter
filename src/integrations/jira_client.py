"""
Sovereign Read/Write Atlassian Jira REST API v3 Client.

Adheres strictly to:
- Constitution Principle I & Sentinel Playbook:
  - Zero-trust credential loading from `.auth/.env` (no hardcoded fallbacks)
  - Strict hostname validation via `urllib.parse.urlparse(url).netloc`
  - Sanitized exceptions (`JiraClientError`) that never leak tokens
- Constitution Principle III & VII:
  - Exponential backoff via `invoke_with_retry` (`src/utils/retry_utils.py`)
  - Strict Pydantic v2 return models (`JiraIssueRecord`)
"""
import os
import re
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse
import requests

from src.database.mongo_client.uuid_manager import UUIDGenerator
from src.schemas.jira_models import IssueType, JiraIssueRecord, PersonaType
from src.utils.correlation import generate_correlation_id
from src.utils.retry_utils import invoke_with_retry

logger = logging.getLogger(__name__)

TASK_ID_REGEX = re.compile(r"\b(T\d{3,})\b")
VALID_PERSONAS: set[str] = {
    "sentinel",
    "bolt",
    "palette",
    "archie",
    "docdoc",
    "dave",
    "crii",
    "jovol",
    "silas",
}


class JiraClientError(Exception):
    """Sanitized exception raised on Jira configuration or API errors."""


class JiraClient:
    """
    Bi-directional client for Atlassian Jira Cloud REST API v3.
    Supports reading issues via JQL, creating Epics/Stories/Tasks,
    transitioning issue workflow states, and posting worklog comments.
    """

    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        project_key: str = "PORTER",
        timeout_seconds: int = 15,
    ) -> None:
        if not base_url or not email or not api_token:
            raise JiraClientError(
                "Missing required Jira configuration (base_url, email, or api_token)."
            )

        parsed = urlparse(base_url.strip())
        if parsed.scheme not in ("https", "http") or not parsed.netloc:
            raise JiraClientError(
                f"Invalid JIRA_BASE_URL '{base_url}': must include scheme and valid hostname."
            )

        self.base_url = f"{parsed.scheme}://{parsed.netloc}"
        self.email = email.strip()
        self.project_key = project_key.strip().upper()
        self.timeout_seconds = timeout_seconds

        self.session = requests.Session()
        self.session.auth = (self.email, api_token.strip())
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    @classmethod
    def from_env(cls, project_key_override: Optional[str] = None) -> "JiraClient":
        """Instantiate JiraClient from `.auth/.env` environment variables."""
        base_url = os.environ.get("JIRA_BASE_URL", "").strip()
        email = os.environ.get("JIRA_EMAIL", "").strip()
        api_token = os.environ.get("JIRA_API_TOKEN", "").strip()
        project_key = (
            project_key_override
            or os.environ.get("JIRA_PROJECT_KEY", "PORTER").strip()
        )

        if not base_url or not email or not api_token:
            raise JiraClientError(
                "Missing required Jira configuration in .auth/.env: "
                "JIRA_BASE_URL, JIRA_EMAIL, and JIRA_API_TOKEN must be set."
            )

        return cls(
            base_url=base_url,
            email=email,
            api_token=api_token,
            project_key=project_key,
        )

    def _request(
        self,
        method: str,
        path: str,
        json_payload: Optional[dict[str, Any]] = None,
        params: Optional[dict[str, Any]] = None,
    ) -> requests.Response:
        """Execute an HTTP request against Jira REST API v3 with exponential backoff."""
        url = f"{self.base_url}{path}"

        def _do_call() -> requests.Response:
            resp = self.session.request(
                method=method,
                url=url,
                json=json_payload,
                params=params,
                timeout=self.timeout_seconds,
            )
            if resp.status_code == 429 or resp.status_code >= 500:
                raise JiraClientError(
                    f"429/5xx transient Jira API error ({resp.status_code}) on {path}"
                )
            return resp

        return invoke_with_retry(_do_call)

    @staticmethod
    def _build_adf_document(text: str) -> dict[str, Any]:
        """Wrap plain text in Atlassian Document Format (ADF) for Jira REST API v3."""
        return {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": text or ""}],
                }
            ],
        }

    @staticmethod
    def _extract_plain_text_from_adf(adf_node: Any) -> str:
        """Extract readable text from an Atlassian Document Format (ADF) payload."""
        if not adf_node:
            return ""
        if isinstance(adf_node, str):
            return adf_node
        if isinstance(adf_node, dict):
            if adf_node.get("type") == "text":
                return str(adf_node.get("text", ""))
            children = adf_node.get("content", [])
            if isinstance(children, list):
                return "\n".join(
                    filter(
                        None,
                        (JiraClient._extract_plain_text_from_adf(c) for c in children),
                    )
                )
        return ""

    @staticmethod
    def _extract_persona_from_labels(labels: list[str]) -> PersonaType:
        """Infer the assigned Jules persona from `jules:<persona>` issue labels."""
        for label in labels:
            lower_lbl = label.lower()
            if lower_lbl.startswith("jules:"):
                candidate = lower_lbl.split(":", 1)[1]
                if candidate in VALID_PERSONAS:
                    return candidate  # type: ignore[return-value]
        return "silas"

    def fetch_issues(
        self,
        user_email: str,
        project_key: Optional[str] = None,
        jql_filter: Optional[str] = None,
        max_results: int = 50,
        correlation_id: Optional[str] = None,
    ) -> list[JiraIssueRecord]:
        """
        Pull issues from Jira using JQL and normalize them into tenant-scoped
        `JiraIssueRecord` models.
        """
        target_project = (project_key or self.project_key).upper()
        jql = jql_filter or f'project = "{target_project}" ORDER BY updated DESC'
        day_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        corr_id = correlation_id or generate_correlation_id(
            user_id=user_email,
            day_str=day_str,
            entry_type="log",
        )

        resp = self._request(
            "GET",
            "/rest/api/3/search/jql",
            params={
                "jql": jql,
                "maxResults": max_results,
                "fields": "summary,status,issuetype,labels,description,parent",
            },
        )
        if resp.status_code != 200:
            raise JiraClientError(
                f"Failed to fetch Jira issues (HTTP {resp.status_code})."
            )

        payload = resp.json()
        raw_issues = payload.get("issues", [])
        records: list[JiraIssueRecord] = []

        for item in raw_issues:
            jira_key = str(item.get("key", "")).strip()
            if not jira_key:
                continue
            fields = item.get("fields", {}) or {}
            summary = str(fields.get("summary") or "Untitled Issue")[:255]
            status_name = str(
                (fields.get("status") or {}).get("name") or "To Do"
            )
            issue_type_raw = str(
                (fields.get("issuetype") or {}).get("name") or "Task"
            )
            issue_type: IssueType = (
                issue_type_raw  # type: ignore[assignment]
                if issue_type_raw in ("Epic", "Story", "Task", "Sub-task")
                else "Task"
            )
            labels = [str(lbl) for lbl in (fields.get("labels") or [])]
            description_text = self._extract_plain_text_from_adf(
                fields.get("description")
            )
            task_match = TASK_ID_REGEX.search(summary)
            task_id = task_match.group(1) if task_match else None
            persona = self._extract_persona_from_labels(labels)
            parent_key = (fields.get("parent") or {}).get("key")

            records.append(
                JiraIssueRecord(
                    uuid=UUIDGenerator.generate_for_jira_issue(jira_key, user_email),
                    user_email=user_email,
                    jira_key=jira_key,
                    project_key=target_project,
                    issue_type=issue_type,
                    task_id=task_id,
                    epic_key=str(parent_key) if parent_key else None,
                    summary=summary,
                    description=description_text[:20000],
                    status=status_name,
                    persona=persona,
                    labels=labels,
                    sync_status="synced",
                    correlation_id=corr_id,
                )
            )

        return records

    def create_issue(
        self,
        summary: str,
        description: str,
        issue_type: IssueType = "Task",
        project_key: Optional[str] = None,
        labels: Optional[list[str]] = None,
        epic_key: Optional[str] = None,
    ) -> str:
        """Create a new issue in Jira and return its created key (e.g. `PORTER-42`)."""
        target_project = (project_key or self.project_key).upper()
        fields: dict[str, Any] = {
            "project": {"key": target_project},
            "summary": summary[:255],
            "description": self._build_adf_document(description[:20000]),
            "issuetype": {"name": issue_type},
        }
        if labels:
            fields["labels"] = labels
        if epic_key:
            fields["parent"] = {"key": epic_key}

        resp = self._request(
            "POST",
            "/rest/api/3/issue",
            json_payload={"fields": fields},
        )
        if resp.status_code not in (200, 201):
            raise JiraClientError(
                f"Failed to create Jira issue (HTTP {resp.status_code})."
            )
        data = resp.json()
        created_key = str(data.get("key", "")).strip()
        if not created_key:
            raise JiraClientError("Jira API did not return an issue key.")
        return created_key

    def transition_issue(self, jira_key: str, target_status: str) -> bool:
        """Transition a Jira issue to `target_status` (case-insensitive match)."""
        resp = self._request("GET", f"/rest/api/3/issue/{jira_key}/transitions")
        if resp.status_code != 200:
            raise JiraClientError(
                f"Failed to retrieve transitions for {jira_key} (HTTP {resp.status_code})."
            )
        transitions = resp.json().get("transitions", [])
        transition_id: Optional[str] = None
        for tr in transitions:
            if str(tr.get("name", "")).strip().lower() == target_status.strip().lower():
                transition_id = str(tr.get("id"))
                break

        if not transition_id:
            logger.warning(
                "Target transition '%s' not available for Jira issue %s.",
                target_status,
                jira_key,
            )
            return False

        post_resp = self._request(
            "POST",
            f"/rest/api/3/issue/{jira_key}/transitions",
            json_payload={"transition": {"id": transition_id}},
        )
        return post_resp.status_code in (200, 204)

    def add_comment(self, jira_key: str, comment_text: str) -> bool:
        """Append an ADF comment to a Jira issue (used for worklogs & Jules lineage)."""
        resp = self._request(
            "POST",
            f"/rest/api/3/issue/{jira_key}/comment",
            json_payload={"body": self._build_adf_document(comment_text)},
        )
        return resp.status_code in (200, 201)
