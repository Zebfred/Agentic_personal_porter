"""Audit Inspector agent for tenant-scoped event verification and ground-truth promotion."""

from datetime import datetime, timezone
from typing import Dict, List

from pymongo import UpdateOne

from src.config import MongoConfig
from src.database.mongo_client.connection import MongoConnectionManager
from src.database.mongo_client.hub_storage import execute_safe_bulk_write
from src.database.mongo_client.uuid_manager import UUIDGenerator
from src.services.tenant_context import resolve_tenant_username


class AuditInspector:
    """Analyzes categorized records and batches unverified items for human-in-the-loop review."""

    def __init__(self) -> None:
        self.db = MongoConnectionManager.get_db()
        self.daily_col = self.db[MongoConfig.DAILY_CATEGORIZED_EVENTS]
        self.actual_col = self.db[MongoConfig.ACTUAL_COLLECTION]
        self.unified_col = self.db[MongoConfig.UNIFIED_EVENTS_COLLECTION]

    def batch_unverified_records(
        self, user_email: str, *, username: str | None = None
    ) -> List[Dict]:
        """Retrieve recent unverified records for the tenant, sorted lowest confidence first."""
        from src.database.mongo_client.agent_health import AgentHeartbeatManager

        resolved_username = resolve_tenant_username(user_email, jwt_username=username)
        health_manager = AgentHeartbeatManager()
        run_id = health_manager.start_agent_run(
            "audit_inspector",
            {"action": "batch_unverified_records", "user_email": user_email},
            username=resolved_username,
        )
        try:
            records = list(
                self.daily_col.find(
                    {"status": "Pending Verification", "user_email": user_email}
                ).limit(10)
            )
            for rec in records:
                if "_id" in rec:
                    rec["_id"] = str(rec["_id"])
                rec.setdefault("confidence_score", 0)
                rec.setdefault("username", resolved_username)
            records.sort(key=lambda x: x["confidence_score"])
            health_manager.end_agent_run(
                run_id, status="success", result_summary=f"Found {len(records)} unverified."
            )
            return records
        except Exception as exc:
            health_manager.end_agent_run(run_id, status="fail", error_msg=str(exc))
            raise

    def get_recently_verified_records(
        self, user_email: str, limit: int = 10, *, username: str | None = None
    ) -> List[Dict]:
        """Retrieve the tenant's most recently verified records for the Dashboard ledger."""
        resolved_username = resolve_tenant_username(user_email, jwt_username=username)
        records = list(
            self.daily_col.find({"status": "Verified", "user_email": user_email})
            .sort("verification_time", -1)
            .limit(limit)
        )
        for rec in records:
            if "_id" in rec:
                rec["_id"] = str(rec["_id"])
            rec.setdefault("username", resolved_username)
        return records

    def _build_approval_ops(
        self, records: List[Dict], user_email: str, resolved_username: str
    ) -> tuple[list[UpdateOne], list[UpdateOne], list[UpdateOne]]:
        """Construct tenant-scoped bulk_write operations for actuals, unified, and daily."""
        actual_ops: list[UpdateOne] = []
        unified_ops: list[UpdateOne] = []
        daily_ops: list[UpdateOne] = []
        now_utc = datetime.now(timezone.utc)
        now_iso = now_utc.isoformat()

        for rec in records:
            gcal_id = rec.get("gcal_id")
            event_uuid = UUIDGenerator.generate_for_event(gcal_id, user_email)
            actual_payload = {
                "title": rec.get("title", "Untitled"),
                "category": rec.get("pillar"),
                "energy_spent": rec.get("duration_minutes", 60),
                "status": "Verified",
            }
            actual_doc = {
                "user_id": user_email,
                "user_email": user_email,
                "username": resolved_username,
                "gcal_id": gcal_id,
                "time_slot": {"start": rec.get("start"), "end": rec.get("end", rec.get("start"))},
                "actual": actual_payload,
                "metadata": {"source": "verification_dashboard", "last_sync": now_iso},
            }
            actual_ops.append(UpdateOne({"_id": event_uuid}, {"$set": actual_doc}, upsert=True))
            unified_ops.append(
                UpdateOne(
                    {"_id": event_uuid},
                    {
                        "$set": {
                            "user_id": user_email,
                            "username": resolved_username,
                            "actual": actual_payload,
                        }
                    },
                )
            )
            daily_ops.append(
                UpdateOne(
                    {"_id": rec["_id"], "user_email": user_email},
                    {
                        "$set": {
                            "status": "Verified",
                            "username": resolved_username,
                            "verified_by": resolved_username,
                            "verification_time": now_utc,
                        }
                    },
                )
            )
        return actual_ops, unified_ops, daily_ops

    def approve_batch(
        self, gcal_ids: List[str], user_email: str, *, username: str | None = None
    ) -> int:
        """Mark tenant records verified and promote them to event_actuals ground truth."""
        from src.database.mongo_client.agent_health import AgentHeartbeatManager

        resolved_username = resolve_tenant_username(user_email, jwt_username=username)
        health_manager = AgentHeartbeatManager()
        run_id = health_manager.start_agent_run(
            "audit_inspector",
            {"action": "approve_batch", "user_email": user_email, "count": len(gcal_ids)},
            username=resolved_username,
        )
        try:
            records = list(
                self.daily_col.find(
                    {
                        "gcal_id": {"$in": gcal_ids},
                        "status": "Pending Verification",
                        "user_email": user_email,
                    },
                    {
                        "gcal_id": 1,
                        "title": 1,
                        "pillar": 1,
                        "duration_minutes": 1,
                        "start": 1,
                        "end": 1,
                    },
                )
            )
            if not records:
                health_manager.end_agent_run(run_id, status="success", result_summary="Approved 0.")
                return 0
            actual_ops, unified_ops, daily_ops = self._build_approval_ops(
                records, user_email, resolved_username
            )
            if actual_ops:
                execute_safe_bulk_write(self.actual_col, actual_ops)
            if unified_ops:
                execute_safe_bulk_write(self.unified_col, unified_ops)
            counts = execute_safe_bulk_write(self.daily_col, daily_ops)
            modified_count = int(counts["modified_count"])
            health_manager.end_agent_run(
                run_id, status="success", result_summary=f"Approved {modified_count}."
            )
            return modified_count
        except Exception as exc:
            health_manager.end_agent_run(run_id, status="fail", error_msg=str(exc))
            raise
