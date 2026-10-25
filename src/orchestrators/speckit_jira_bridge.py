r"""
Spec-Kit ↔ Atlassian Jira ↔ Google Jules Bridge Orchestrator & CLI.

Parses `specs/NNN-feature/spec.md`, `plan.md`, and `tasks.md`:
1. Extracts canonical task IDs (`\bT\d{3,}\b`), `[P]` parallel flags, `[US#]` labels, and target file paths.
2. Automatically maps tasks to the 8 `.jules/<persona>.md` profiles (`sentinel`, `bolt`, `palette`, `archie`, `docdoc`, `dave`, `crii`, `jovol`) or `silas`.
3. Deduplicates tasks against existing local/remote Jira issues (`SC-002`).
4. Formats and dispatches eligible tasks to `@google/jules` via `JulesDispatcher`.
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.database.mongo_client.jira_storage import JiraStorage
from src.database.mongo_client.uuid_manager import UUIDGenerator
from src.integrations.jira_client import JiraClient, JiraClientError
from src.integrations.jules_dispatcher import JulesDispatcher
from src.schemas.jira_models import JiraIssueRecord, PersonaType, SpecKitTaskItem
from src.utils.correlation import generate_correlation_id
from src.utils.path_utils import get_project_root

logger = logging.getLogger(__name__)

TASK_LINE_REGEX = re.compile(
    r"^\s*-\s*\[(?P<checked>[ xX])\]\s*(?P<task_id>T\d{3,})\s*(?P<rest>.+)$"
)
PARALLEL_MARKER_REGEX = re.compile(r"\[P\]")
STORY_MARKER_REGEX = re.compile(r"\[(US\d+)\]")
FILE_PATH_REGEX = re.compile(
    r"`?((?:src|tests|frontend|documentation|scripts|\.specify|\.jules)/[A-Za-z0-9_./-]+|"
    r"Makefile|Dockerfile|docker-compose\.yml)`?"
)


def infer_persona_for_task(description: str, target_paths: list[str]) -> PersonaType:
    """
    Map a Spec-Kit task to its primary `.jules/<persona>.md` profile based on
    target files and domain keywords (`FR-007`).
    """
    combined = f"{description} {' '.join(target_paths)}".lower()

    if any(
        k in combined
        for k in ("auth_middleware", "zero-trust", "hmac", "urlparse", "security", "sentinel")
    ):
        return "sentinel"
    if any(
        k in combined
        for k in ("bulk_write", "projection", "jira_storage", "mongo_client", "neo4j", "bolt")
    ):
        return "bolt"
    if any(k in combined for k in ("frontend/", ".html", "wcag", "aria-label", "css", "palette")):
        return "palette"
    if any(k in combined for k in ("frontend/js", "spec-kit/", "component", "jovol")):
        return "jovol"
    if any(
        k in combined for k in ("tests/unit/", "adversarial", "null-byte", "resilience", "crii")
    ):
        return "crii"
    if any(k in combined for k in ("src/schemas/", "pydantic", "architecture", "archie")):
        return "archie"
    if any(k in combined for k in ("documentation/", ".legacy_hr", "kebab-case", "docdoc")):
        return "docdoc"
    if any(
        k in combined
        for k in ("dockerfile", "docker-compose", "makefile", ".github/workflows", "dave")
    ):
        return "dave"
    return "silas"


def parse_speckit_tasks_markdown(
    tasks_path: Path,
    feature_id: str,
) -> list[SpecKitTaskItem]:
    r"""
    Parse a Spec-Kit `tasks.md` file into validated `SpecKitTaskItem` objects.
    Handles task IDs of 3 or more digits (`\bT\d{3,}\b`, e.g., `T001`, `T1000`).
    """
    if not tasks_path.exists():
        raise FileNotFoundError(f"Tasks file not found: {tasks_path}")

    items: list[SpecKitTaskItem] = []
    for raw_line in tasks_path.read_text(encoding="utf-8").splitlines():
        match = TASK_LINE_REGEX.match(raw_line)
        if not match:
            continue

        checked = match.group("checked").lower() == "x"
        task_id = match.group("task_id")
        rest = match.group("rest").strip()

        is_parallel = bool(PARALLEL_MARKER_REGEX.search(rest))
        story_match = STORY_MARKER_REGEX.search(rest)
        user_story = story_match.group(1) if story_match else None

        # Strip [P] and [US#] markers to form clean summary text
        clean_desc = PARALLEL_MARKER_REGEX.sub("", rest)
        clean_desc = STORY_MARKER_REGEX.sub("", clean_desc).strip()

        raw_paths = FILE_PATH_REGEX.findall(clean_desc)
        target_paths = list(dict.fromkeys(raw_paths))
        persona = infer_persona_for_task(clean_desc, target_paths)
        short_title = f"{task_id}: {clean_desc}"[:255]

        items.append(
            SpecKitTaskItem(
                task_id=task_id,
                feature_id=feature_id,
                title=short_title,
                description=clean_desc,
                is_parallel=is_parallel,
                user_story=user_story,
                target_paths=target_paths,
                persona=persona,
                completed=checked,
            )
        )

    return items


def _resolve_task_jira_key(
    item: SpecKitTaskItem,
    formatted_desc: str,
    project_key: str,
    labels: list[str],
    epic_key: str,
    dry_run: bool,
    jira_client: Optional[JiraClient],
) -> tuple[str, str]:
    """Determine `(jira_key, sync_state)` for a Spec-Kit task item."""
    if dry_run:
        return f"LOCAL-{item.task_id}", "synced"
    if jira_client is None:
        return f"LOCAL-{item.task_id}", "pending_upstream"
    try:
        key = jira_client.create_issue(
            summary=item.title,
            description=formatted_desc,
            issue_type="Task",
            project_key=project_key,
            labels=labels,
            epic_key=epic_key if not epic_key.startswith("LOCAL-") else None,
        )
        return key, "synced"
    except JiraClientError as exc:
        logger.warning("Queued %s as pending_upstream due to Jira error: %s", item.task_id, exc)
        return f"LOCAL-{item.task_id}", "pending_upstream"


def _create_or_stage_task_record(
    item: SpecKitTaskItem,
    feature_id: str,
    spec_excerpt: str,
    user_email: str,
    project_key: str,
    epic_key: str,
    correlation_id: str,
    dry_run: bool,
    jira_client: Optional[JiraClient],
) -> tuple[JiraIssueRecord, dict[str, Any]]:
    """Create a remote or local Jira issue for a single Spec-Kit task item."""
    labels = ["speckit", f"feature:{feature_id}", f"jules:{item.persona}"]
    if item.is_parallel:
        labels.append("parallel")
    if item.user_story:
        labels.append(item.user_story.lower())

    formatted_desc = (
        f"Feature: {feature_id}\nTask ID: {item.task_id}\n"
        f"User Story: {item.user_story or 'Shared/Foundation'}\n"
        f"Assigned Persona: {item.persona}\n"
        f"Target Paths: {', '.join(item.target_paths) or 'N/A'}\n\n"
        f"Task Requirement:\n{item.description}\n\n"
        f"Specification Context:\n{spec_excerpt[:1000]}"
    )
    jira_key, sync_state = _resolve_task_jira_key(
        item, formatted_desc, project_key, labels, epic_key, dry_run, jira_client
    )
    record = JiraIssueRecord(
        uuid=UUIDGenerator.generate_for_jira_issue(jira_key, user_email),
        user_email=user_email,
        jira_key=jira_key,
        project_key=project_key,
        issue_type="Task",
        task_id=item.task_id,
        feature_id=feature_id,
        epic_key=epic_key,
        summary=item.title,
        description=formatted_desc,
        status="Done" if item.completed else "To Do",
        persona=item.persona,
        labels=labels,
        sync_status=sync_state,  # type: ignore[arg-type]
        correlation_id=correlation_id,
    )
    summary_dict = {
        "task_id": item.task_id,
        "jira_key": jira_key,
        "summary": item.title,
        "persona": item.persona,
        "is_parallel": item.is_parallel,
    }
    return record, summary_dict


def _resolve_epic_key(
    feature_id: str,
    spec_excerpt: str,
    project_key: str,
    dry_run: bool,
    jira_client: Optional[JiraClient],
) -> str:
    """Create or resolve the parent Epic key for a Spec-Kit feature."""
    epic_key = f"{project_key}-EPIC" if dry_run else f"{project_key}-1"
    if not dry_run and jira_client is not None:
        try:
            epic_key = jira_client.create_issue(
                summary=f"[Spec-Kit Epic] {feature_id}",
                description=spec_excerpt,
                issue_type="Epic",
                project_key=project_key,
                labels=["speckit", f"feature:{feature_id}"],
            )
        except JiraClientError as exc:
            logger.warning("Epic creation fallback triggered: %s", exc)
            epic_key = "LOCAL-T000"
    return epic_key


def _read_spec_excerpt(spec_file: Path, feature_id: str) -> str:
    """Return up to 2000 characters from `spec.md`, or a fallback label."""
    return (
        spec_file.read_text(encoding="utf-8")[:2000]
        if spec_file.exists()
        else f"Feature {feature_id}"
    )


def sync_feature_to_jira(
    feature_dir: Path,
    user_email: str,
    project_key: str = "PORTER",
    dry_run: bool = True,
    storage: Optional[JiraStorage] = None,
    jira_client: Optional[JiraClient] = None,
) -> dict[str, Any]:
    """Synchronize a Spec-Kit feature directory (`spec.md`, `tasks.md`) into Jira issues."""
    resolved_dir = feature_dir.resolve()
    feature_id = resolved_dir.name
    task_items = parse_speckit_tasks_markdown(resolved_dir / "tasks.md", feature_id=feature_id)
    spec_excerpt = _read_spec_excerpt(resolved_dir / "spec.md", feature_id)
    jira_store = storage or JiraStorage()
    existing_map = jira_store.get_existing_task_mappings(user_email, project_key)
    day_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    correlation_id = generate_correlation_id(user_email, day_str, feature_id[:24], "weekly")
    epic_key = _resolve_epic_key(feature_id, spec_excerpt, project_key, dry_run, jira_client)

    created_tasks: list[dict[str, Any]] = []
    skipped_tasks: list[str] = []
    records_to_upsert: list[JiraIssueRecord] = []

    for item in task_items:
        if item.task_id in existing_map:
            skipped_tasks.append(item.task_id)
            continue
        record, summary_dict = _create_or_stage_task_record(
            item,
            feature_id,
            spec_excerpt,
            user_email,
            project_key,
            epic_key,
            correlation_id,
            dry_run,
            jira_client,
        )
        records_to_upsert.append(record)
        created_tasks.append(summary_dict)

    if not dry_run and records_to_upsert:
        jira_store.bulk_upsert_issues(records_to_upsert)
        jira_store.merge_issues_to_neo4j(records_to_upsert)

    return {
        "status": "success",
        "dry_run": dry_run,
        "feature_id": feature_id,
        "epic_key": epic_key,
        "created_tasks": created_tasks,
        "skipped_tasks": skipped_tasks,
        "correlation_id": correlation_id,
    }


def _resolve_default_feature_dir() -> Path:
    """Resolve the active feature directory from `.specify/feature.json`."""
    root = get_project_root()
    feature_json = root / ".specify" / "feature.json"
    if feature_json.exists():
        data = json.loads(feature_json.read_text(encoding="utf-8"))
        rel = data.get("feature_directory")
        if rel:
            return (root / str(rel)).resolve()
    return (root / "specs" / "002-jira-jules-bridge").resolve()


def _build_bridge_arg_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser for the Spec-Kit / Jira / Jules bridge."""
    parser = argparse.ArgumentParser(
        description="Unified Spec-Kit / Atlassian Jira <-> Google Jules Bridge"
    )
    parser.add_argument(
        "--feature-dir",
        type=str,
        default=None,
        help="Path to Spec-Kit feature directory (defaults to .specify/feature.json)",
    )
    parser.add_argument("--project-key", type=str, default="PORTER", help="Target Jira project key")
    parser.add_argument(
        "--user-email",
        type=str,
        default="system_script@localhost",
        help="Tenant user_email for scoping records",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview formatted Jira/Jules payloads without mutating remote systems",
    )
    parser.add_argument(
        "--push", action="store_true", default=False, help="Push Spec-Kit tasks live"
    )
    parser.add_argument(
        "--dispatch-task",
        type=str,
        default=None,
        help="Task ID (e.g. T001) to format/dispatch as a Google Jules work order",
    )
    parser.add_argument(
        "--execute-jules",
        action="store_true",
        default=False,
        help="Invoke @google/jules CLI live for --dispatch-task",
    )
    return parser


def _handle_cli_dispatch_task(args: argparse.Namespace, feature_dir: Path) -> int:
    """Handle the `--dispatch-task` CLI workflow."""
    items = parse_speckit_tasks_markdown(feature_dir / "tasks.md", feature_id=feature_dir.name)
    matched = next((t for t in items if t.task_id == args.dispatch_task.strip().upper()), None)
    if not matched:
        print(
            f"Error: Task '{args.dispatch_task}' not found in {feature_dir / 'tasks.md'}",
            file=sys.stderr,
        )
        return 1

    issue_rec = JiraIssueRecord(
        uuid=UUIDGenerator.generate_for_jira_issue(f"LOCAL-{matched.task_id}", args.user_email),
        user_email=args.user_email,
        jira_key=f"LOCAL-{matched.task_id}",
        project_key=args.project_key.upper(),
        task_id=matched.task_id,
        feature_id=feature_dir.name,
        summary=matched.title,
        description=matched.description,
        persona=matched.persona,
        correlation_id=f"cli-{feature_dir.name}-{matched.task_id}",
    )
    dispatcher = JulesDispatcher()
    work_order = dispatcher.build_work_order(
        issue=issue_rec,
        target_paths=matched.target_paths,
        dry_run=not args.execute_jules,
    )
    if args.execute_jules:
        work_order = dispatcher.dispatch_work_order(work_order=work_order)
    print(json.dumps(work_order.model_dump(), indent=2))
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entrypoint for Spec-Kit ↔ Jira ↔ Jules bridge."""
    parser = _build_bridge_arg_parser()
    args = parser.parse_args(argv)
    feature_dir = (
        Path(args.feature_dir).resolve() if args.feature_dir else _resolve_default_feature_dir()
    )
    is_dry_run = args.dry_run or not (args.push or args.execute_jules)

    if args.dispatch_task:
        return _handle_cli_dispatch_task(args, feature_dir)

    client: Optional[JiraClient] = None
    if args.push and not is_dry_run:
        try:
            client = JiraClient.from_env(project_key_override=args.project_key)
        except JiraClientError as exc:
            logger.warning("Proceeding with local pending_upstream queue: %s", exc)

    result = sync_feature_to_jira(
        feature_dir=feature_dir,
        user_email=args.user_email,
        project_key=args.project_key.upper(),
        dry_run=is_dry_run,
        jira_client=client,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
