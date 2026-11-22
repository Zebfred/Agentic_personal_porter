"""MongoDB storage operations for North Star Accountability (004)."""

from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from pymongo import ASCENDING, DESCENDING, UpdateOne

from src.config import MongoConfig
from src.database.mongo_client.hub_storage import execute_safe_bulk_write
from src.schemas.accountability_models import (
    GraceWindowRequest,
    NorthStarPillar,
    ReconCheckInRequest,
)

logger = logging.getLogger("APP_ROUTER")

PILLAR_PROJECTION: dict[str, int] = {
    "_id": 0,
    "user_email": 1,
    "pillar_id": 1,
    "title": 1,
    "category": 1,
    "weekly_target_count": 1,
    "target_unit": 1,
    "is_restorative_life_pillar": 1,
    "grace_eligible": 1,
    "active": 1,
}
RECON_LOG_PROJECTION: dict[str, int] = {
    "_id": 0,
    "entry_uuid": 1,
    "user_email": 1,
    "pillar_id": 1,
    "iso_date": 1,
    "iso_week": 1,
    "minutes_spent": 1,
    "win_note": 1,
    "idempotency_key": 1,
    "source": 1,
}
GRACE_PROJECTION: dict[str, int] = {
    "_id": 0,
    "user_email": 1,
    "iso_week": 1,
    "enabled": 1,
    "reason": 1,
}
_ACCOUNTABILITY_NS = uuid.UUID("7f3b9a84-4e21-4d30-9f5c-11b02f94c004")


def iso_week_from_date(iso_date: str) -> str:
    """Convert YYYY-MM-DD into strict ISO week notation (YYYY-Www)."""
    iso_year, iso_wk, _ = datetime.strptime(iso_date, "%Y-%m-%d").date().isocalendar()
    return f"{iso_year:04d}-W{iso_wk:02d}"


def build_entry_uuid(user_email: str, pillar_id: str, idempotency_key: str) -> str:
    """Generate a deterministic tenant-scoped UUIDv5 for a recon win entry."""
    return str(uuid.uuid5(_ACCOUNTABILITY_NS, f"{user_email}::{pillar_id}::{idempotency_key}"))


def ensure_accountability_indexes(db: Any) -> None:
    """Create compound tenant indexes safely (non-fatal if backend is offline)."""
    try:
        db[MongoConfig.NORTH_STAR_PILLARS_COLLECTION].create_index(
            [("user_email", ASCENDING), ("pillar_id", ASCENDING)],
            unique=True,
            name="idx_pillar_tenant_id_unique",
        )
        db[MongoConfig.PILLAR_CHECKINS_COLLECTION].create_index(
            [("user_email", ASCENDING), ("idempotency_key", ASCENDING)],
            unique=True,
            name="idx_recon_tenant_idempotency_unique",
        )
        db[MongoConfig.PILLAR_CHECKINS_COLLECTION].create_index(
            [("user_email", ASCENDING), ("iso_week", DESCENDING), ("pillar_id", ASCENDING)],
            name="idx_recon_tenant_week_pillar",
        )
        db[MongoConfig.GRACE_WINDOWS_COLLECTION].create_index(
            [("user_email", ASCENDING), ("iso_week", ASCENDING)],
            unique=True,
            name="idx_grace_tenant_week_unique",
        )
    except Exception as exc:
        logger.warning("Accountability index initialization skipped: %s", exc)


def upsert_pillars_batch(
    db: Any, user_email: str, pillars: list[NorthStarPillar]
) -> dict[str, int]:
    """Batch-upsert tenant-scoped North Star pillars via safe bulk_write."""
    col = db[MongoConfig.NORTH_STAR_PILLARS_COLLECTION]
    now_iso = datetime.now(timezone.utc).isoformat()
    ops = [
        UpdateOne(
            {"user_email": user_email, "pillar_id": p.pillar_id},
            {
                "$set": {
                    **p.model_dump(mode="json"),
                    "user_email": user_email,
                    "updated_at": now_iso,
                }
            },
            upsert=True,
        )
        for p in pillars
    ]
    return {"saved_count": len(ops), **execute_safe_bulk_write(col, ops)}


def list_tenant_pillars(
    db: Any, user_email: str, *, active_only: bool = True
) -> list[dict[str, Any]]:
    """Return projected North Star pillars scoped strictly to user_email."""
    query: dict[str, Any] = {"user_email": user_email}
    if active_only:
        query["active"] = True
    return list(
        db[MongoConfig.NORTH_STAR_PILLARS_COLLECTION]
        .find(query, PILLAR_PROJECTION)
        .sort("pillar_id", ASCENDING)
    )


def record_recon_win(
    db: Any, user_email: str, payload: ReconCheckInRequest
) -> tuple[dict[str, Any], bool]:
    """Persist an idempotent 20-Second Recon win. Returns (record, created)."""
    col = db[MongoConfig.PILLAR_CHECKINS_COLLECTION]
    existing = col.find_one(
        {"user_email": user_email, "idempotency_key": payload.idempotency_key},
        RECON_LOG_PROJECTION,
    )
    if existing is not None:
        return dict(existing), False

    record: dict[str, Any] = {
        "entry_uuid": build_entry_uuid(user_email, payload.pillar_id, payload.idempotency_key),
        "user_email": user_email,
        "pillar_id": payload.pillar_id,
        "iso_date": payload.iso_date,
        "iso_week": iso_week_from_date(payload.iso_date),
        "minutes_spent": payload.minutes_spent,
        "win_note": payload.win_note,
        "idempotency_key": payload.idempotency_key,
        "source": payload.source,
    }
    col.insert_one(dict(record))
    return record, True


def list_tenant_recon_wins(db: Any, user_email: str) -> list[dict[str, Any]]:
    """Fetch projected recon wins for a tenant ordered newest ISO week first."""
    return list(
        db[MongoConfig.PILLAR_CHECKINS_COLLECTION]
        .find({"user_email": user_email}, RECON_LOG_PROJECTION)
        .sort("iso_week", DESCENDING)
    )


def upsert_grace_window(db: Any, user_email: str, payload: GraceWindowRequest) -> dict[str, Any]:
    """Store or update a tenant Grace / Vacation Mode window for an ISO week."""
    doc = {
        "user_email": user_email,
        "iso_week": payload.iso_week,
        "enabled": payload.enabled,
        "reason": payload.reason,
    }
    db[MongoConfig.GRACE_WINDOWS_COLLECTION].update_one(
        {"user_email": user_email, "iso_week": payload.iso_week},
        {"$set": doc},
        upsert=True,
    )
    return doc


def list_enabled_grace_weeks(db: Any, user_email: str) -> set[str]:
    """Return the set of ISO weeks where Grace Mode is active for the tenant."""
    docs = db[MongoConfig.GRACE_WINDOWS_COLLECTION].find(
        {"user_email": user_email, "enabled": True}, GRACE_PROJECTION
    )
    return {str(d["iso_week"]) for d in docs}
