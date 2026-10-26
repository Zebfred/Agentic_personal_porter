"""
Focused MongoDB Storage Operations for First-Serving Hub API (`003-first-serving-hub-api`).

Handles `events_to_be_classified` batched staging, `calculate_hub_metrics()`,
and `save_weekly_intentions_batch()` one-shot weekly planning persistence.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from pymongo import ASCENDING, DESCENDING, UpdateOne

from src.config import MongoConfig
from src.database.mongo_client.uuid_manager import UUIDGenerator
from src.schemas.hub_models import (
    EventToBeClassified,
    EventToBeClassifiedInput,
    HubProgressMetrics,
    WeeklyIntentionItem,
    WeeklyPlanningRequestSchema,
)
from src.utils.correlation import generate_correlation_id

CLASSIFICATION_PROJECTION: dict[str, int] = {
    "_id": 0,
    "uuid": 1,
    "user_email": 1,
    "gcal_id": 1,
    "summary": 1,
    "start_time": 1,
    "end_time": 1,
    "suggested_pillar": 1,
    "confidence_score": 1,
    "status": 1,
    "correlation_id": 1,
}


def execute_safe_bulk_write(collection: Any, ops: list[UpdateOne]) -> dict[str, int]:
    """Execute batched `bulk_write(ops, ordered=False)` with PyMongo 4.11+ mongomock fallback."""
    if not ops:
        return {"upserted_count": 0, "modified_count": 0}
    try:
        res = collection.bulk_write(ops, ordered=False)
        return {
            "upserted_count": int(getattr(res, "upserted_count", 0) or 0),
            "modified_count": int(getattr(res, "modified_count", 0) or 0),
        }
    except TypeError as exc:
        if "sort" not in str(exc):
            raise
        upserted, modified = 0, 0
        for op in ops:
            r = collection.update_one(op._filter, op._doc, upsert=op._upsert)
            if getattr(r, "upserted_id", None) is not None:
                upserted += 1
            elif int(getattr(r, "modified_count", 0) or 0) > 0:
                modified += 1
        return {"upserted_count": upserted, "modified_count": modified}


def ensure_hub_indexes(db: Any) -> None:
    """Create compound indexes for `events_to_be_classified`."""
    col = db[MongoConfig.EVENTS_TO_BE_CLASSIFIED_COLLECTION]
    col.create_index(
        [("user_email", ASCENDING), ("status", ASCENDING), ("start_time", DESCENDING)],
        name="idx_classify_tenant_status_start",
    )
    col.create_index([("uuid", ASCENDING)], unique=True, name="idx_classify_uuid_unique")


def stage_events_for_classification(
    db: Any, user_email: str, events: list[EventToBeClassifiedInput]
) -> dict[str, int]:
    """Batch-upsert unclassified calendar events into `events_to_be_classified`."""
    col = db[MongoConfig.EVENTS_TO_BE_CLASSIFIED_COLLECTION]
    ops: list[UpdateOne] = []
    for item in events:
        event_uuid = UUIDGenerator.generate_for_event(item.gcal_id, user_email)
        cid = generate_correlation_id(user_email, item.start_time[:10], item.gcal_id, "classify")
        record = EventToBeClassified(
            uuid=event_uuid,
            user_email=user_email,
            gcal_id=item.gcal_id,
            summary=item.summary,
            start_time=item.start_time,
            end_time=item.end_time,
            suggested_pillar=item.suggested_pillar or "Uncategorized",
            confidence_score=item.confidence_score,
            status="pending_classification",
            correlation_id=cid,
        )
        ops.append(
            UpdateOne(
                {"uuid": event_uuid, "user_email": user_email},
                {"$set": record.model_dump(mode="json")},
                upsert=True,
            )
        )
    counts = execute_safe_bulk_write(col, ops)
    return {"staged_count": len(ops), **counts}


def get_events_to_be_classified(db: Any, user_email: str, limit: int = 50) -> list[dict[str, Any]]:
    """Return pending unclassified calendar events for a tenant using explicit projections."""
    col = db[MongoConfig.EVENTS_TO_BE_CLASSIFIED_COLLECTION]
    query = {"user_email": user_email, "status": "pending_classification"}
    return list(
        col.find(query, CLASSIFICATION_PROJECTION).sort("start_time", DESCENDING).limit(limit)
    )


def calculate_hub_metrics(db: Any, user_email: str) -> HubProgressMetrics:
    """Compute all 6 Hub Progress Metrics and week-over-week Detrimental Detour improvement."""
    intentions_count = db[MongoConfig.INTENT_COLLECTION].count_documents({"user_id": user_email})
    actual_col = db[MongoConfig.ACTUAL_COLLECTION]
    unified_col = db[MongoConfig.UNIFIED_EVENTS_COLLECTION]
    actuals_count = actual_col.count_documents(
        {"user_id": user_email}
    ) + unified_col.count_documents({"user_id": user_email})
    queued_classify = db[MongoConfig.EVENTS_TO_BE_CLASSIFIED_COLLECTION].count_documents(
        {"user_email": user_email, "status": "pending_classification"}
    )
    raw_staged = db[MongoConfig.RAW_TIMESERIES_COLLECTION].count_documents(
        {"metadata.user_email": user_email, "metadata.sync_status": "staged"}
    )
    matched_count = unified_col.count_documents({"user_id": user_email})
    valuable = actual_col.count_documents({"user_id": user_email, "actual.detour_type": "valuable"})
    detrimental = actual_col.count_documents(
        {"user_id": user_email, "actual.detour_type": "detrimental"}
    )

    now = datetime.now(timezone.utc)
    cur_start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    prev_start = (now - timedelta(days=14)).strftime("%Y-%m-%d")
    cur_det = actual_col.count_documents(
        {
            "user_id": user_email,
            "actual.detour_type": "detrimental",
            "time_slot.start": {"$gte": cur_start},
        }
    )
    prev_det = actual_col.count_documents(
        {
            "user_id": user_email,
            "actual.detour_type": "detrimental",
            "time_slot.start": {"$gte": prev_start, "$lt": cur_start},
        }
    )
    imp_pct = round(((prev_det - cur_det) / prev_det) * 100.0, 1) if prev_det > 0 else 0.0
    delta_str = f"{'↓' if imp_pct >= 0 else '↑'} {abs(int(round(imp_pct)))}%"

    return HubProgressMetrics(
        user_email=user_email,
        intentions=intentions_count,
        calendar_events=actuals_count,
        unclassified=queued_classify + raw_staged,
        matched=matched_count,
        valuable_detours=valuable,
        detrimental_detours=detrimental,
        detrimental_improvement_pct=imp_pct,
        detrimental_delta=delta_str,
    )


def save_weekly_intentions_batch(
    db: Any, user_email: str, username: str, payload: WeeklyPlanningRequestSchema
) -> dict[str, Any]:
    """Parse and batch-persist a week of intentions into `event_intentions` and `weekly_expectations`."""
    updated_at = datetime.now(timezone.utc).isoformat()
    cid = generate_correlation_id(
        user_id=username, day_str=payload.week_start_date, entry_type="weekly"
    )
    items = list(payload.intentions)
    if not items and payload.expectation_text:
        for raw_line in payload.expectation_text.splitlines():
            cleaned = raw_line.strip().lstrip("-*•0123456789.) ").strip()
            if cleaned:
                items.append(WeeklyIntentionItem(title=cleaned[:500]))

    ops: list[UpdateOne] = []
    for idx, item in enumerate(items):
        intent_uuid = UUIDGenerator.generate_for_event(
            f"{payload.week_start_date}::{idx}::{item.title[:40]}", user_email
        )
        slot_day = item.start_date or item.day or payload.week_start_date
        doc = {
            "uuid": intent_uuid,
            "user_id": user_email,
            "username": username,
            "week_start_date": payload.week_start_date,
            "title": item.title,
            "pillar": item.pillar,
            "priority": item.priority,
            "intent": {
                "title": item.title,
                "pillar": item.pillar,
                "priority": item.priority,
                "duration_minutes": item.duration_minutes,
            },
            "time_slot": {"start": f"{slot_day}T09:00:00Z", "chunk": item.time_chunk or "weekly"},
            "correlation_id": cid,
            "updated_at": updated_at,
        }
        ops.append(
            UpdateOne({"uuid": intent_uuid, "user_id": user_email}, {"$set": doc}, upsert=True)
        )

    counts = execute_safe_bulk_write(db[MongoConfig.INTENT_COLLECTION], ops)
    summary_text = payload.expectation_text or "\n".join(f"- {i.title}" for i in items)
    db["weekly_expectations"].update_one(
        {"user_id": username, "week_start_date": payload.week_start_date},
        {
            "$set": {
                "user_email": user_email,
                "expectation_text": summary_text,
                "updated_at": updated_at,
                "correlation_id": cid,
                "saga_status": "GRAPH_INJECTED",
            }
        },
        upsert=True,
    )
    return {
        "status": "success",
        "week_start_date": payload.week_start_date,
        "intentions_saved": len(ops),
        "persisted_intentions_count": len(ops),
        "expectation_saved": True,
        "correlation_id": cid,
        "updated_at": updated_at,
        **counts,
    }
