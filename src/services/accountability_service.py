"""Service orchestration for North Star Accountability & Weekly Streaks (004)."""

from collections import defaultdict
from typing import Any

from src.database.accountability_graph import sync_pillar_win_to_graph
from src.database.mongo_client.accountability_storage import (
    ensure_accountability_indexes,
    list_enabled_grace_weeks,
    list_tenant_pillars,
    list_tenant_recon_wins,
    record_recon_win,
    upsert_grace_window,
    upsert_pillars_batch,
)
from src.schemas.accountability_models import (
    AccountabilityDashboardResponse,
    GraceWindowRequest,
    NorthStarPillar,
    ReconCheckInRequest,
)
from src.services.accountability_streaks import (
    STARTER_PILLARS,
    compute_pillar_streak,
    current_iso_week,
)


def get_pillars_payload(db: Any, user_email: str) -> dict[str, Any]:
    """Fetch tenant pillars or return starter templates when uninitialized."""
    ensure_accountability_indexes(db)
    pillars = list_tenant_pillars(db, user_email, active_only=True)
    return {
        "status": "success",
        "user_email": user_email,
        "pillars": pillars,
        "starter_templates": STARTER_PILLARS if not pillars else [],
    }


def save_pillars_batch(db: Any, user_email: str, pillars: list[NorthStarPillar]) -> dict[str, Any]:
    """Persist up to 6 North Star pillars for a tenant."""
    ensure_accountability_indexes(db)
    return {
        "status": "success",
        "user_email": user_email,
        **upsert_pillars_batch(db, user_email, pillars),
    }


def log_recon_entry(
    db: Any, user_email: str, payload: ReconCheckInRequest
) -> tuple[dict[str, Any], int]:
    """Persist a 20-Second Recon win, trigger optional Neo4j sync, and return refreshed streak."""
    ensure_accountability_indexes(db)
    pillars = {p["pillar_id"]: p for p in list_tenant_pillars(db, user_email, active_only=True)}
    if payload.pillar_id not in pillars:
        return {"error": f"Active pillar '{payload.pillar_id}' not found for tenant."}, 404

    record, created = record_recon_win(db, user_email, payload)
    graph_status = sync_pillar_win_to_graph(user_email, pillars[payload.pillar_id], record)
    dash = build_accountability_dashboard(db, user_email, iso_week=record["iso_week"])
    summary = next(p for p in dash.pillars if p.pillar_id == payload.pillar_id)
    body = {
        "status": "success",
        "created": created,
        "entry": record,
        "graph_sync_status": graph_status,
        "pillar_streak": summary.model_dump(mode="json"),
    }
    return body, (201 if created else 200)


def set_grace_window(db: Any, user_email: str, payload: GraceWindowRequest) -> dict[str, Any]:
    """Enable or disable Grace / Vacation Mode for a specific ISO week."""
    ensure_accountability_indexes(db)
    return {"status": "success", "grace_window": upsert_grace_window(db, user_email, payload)}


def build_accountability_dashboard(
    db: Any, user_email: str, *, iso_week: str | None = None
) -> AccountabilityDashboardResponse:
    """Compute full tenant accountability streaks and life harmony ratio (zero LLM calls)."""
    ensure_accountability_indexes(db)
    target_week = iso_week or current_iso_week()
    pillars = list_tenant_pillars(db, user_email, active_only=True)
    grace_weeks = list_enabled_grace_weeks(db, user_email)

    by_pillar: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for win in list_tenant_recon_wins(db, user_email):
        by_pillar[str(win["pillar_id"])][str(win["iso_week"])] += 1

    summaries = [
        compute_pillar_streak(p, by_pillar[str(p["pillar_id"])], grace_weeks, target_week)
        for p in pillars
    ]
    overall = (
        round(sum(s.completion_ratio for s in summaries) / len(summaries), 4) if summaries else 0.0
    )
    life_items = [s for s in summaries if s.is_restorative_life_pillar]
    life_harmony = (
        round(sum(s.completion_ratio for s in life_items) / len(life_items), 4)
        if life_items
        else overall
    )
    return AccountabilityDashboardResponse(
        user_email=user_email,
        iso_week=target_week,
        grace_mode_active=target_week in grace_weeks,
        life_harmony_ratio=life_harmony,
        overall_completion_ratio=overall,
        pillars=summaries,
    )
