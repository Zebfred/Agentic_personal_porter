from datetime import datetime, timezone
import logging
import uuid

from src.database.mongo_client.connection import MongoConnectionManager
from src.config import MongoConfig

logger = logging.getLogger(__name__)


class AgentHeartbeatManager:
    """
    Manages the health and execution logging for all background agents and orchestrators.
    """

    def __init__(self):
        self.db = MongoConnectionManager.get_db()
        self.collection = self.db[MongoConfig.AGENT_HEALTH_COLLECTION]

    def start_agent_run(self, agent_name: str, context: dict = None, username: str = None) -> str:
        """
        Registers that an agent has started running.
        Returns a unique run_id to pass to end_agent_run.
        """
        run_id = str(uuid.uuid4())
        payload = {
            "_id": run_id,
            "agent_name": agent_name,
            "status": "running",
            "start_time": datetime.now(timezone.utc),
            "end_time": None,
            "duration_seconds": None,
            "context": context or {},
            "result_summary": None,
            "error_msg": None,
            "username": username or "system",
        }

        try:
            self.collection.insert_one(payload)
        except Exception as exc:
            logger.debug("AgentHeartbeatManager start_agent_run skipped: %s", exc)
        return run_id

    def end_agent_run(
        self, run_id: str, status: str, result_summary: str = None, error_msg: str = None
    ):
        """
        Finalizes an agent run, calculating duration and logging success/failure.
        status should typically be "success" or "fail".
        """
        end_time = datetime.now(timezone.utc)

        try:
            # Fetch start time to calculate duration
            record = self.collection.find_one({"_id": run_id})
            duration = None
            if record and record.get("start_time"):
                start_time = record["start_time"]
                # Ensure timezone awareness for subtraction
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                duration = (end_time - start_time).total_seconds()

            update_payload = {
                "$set": {
                    "status": status,
                    "end_time": end_time,
                    "duration_seconds": duration,
                    "result_summary": result_summary,
                    "error_msg": error_msg,
                }
            }

            self.collection.update_one({"_id": run_id}, update_payload)
        except Exception as exc:
            logger.debug("AgentHeartbeatManager end_agent_run skipped: %s", exc)

    def get_all_agent_statuses(self) -> dict:
        """
        Returns a dictionary mapping agent_name to their most recent execution status.
        """
        pipeline = [
            {"$sort": {"start_time": -1}},
            {
                "$group": {
                    "_id": "$agent_name",
                    "latest_run_id": {"$first": "$_id"},
                    "status": {"$first": "$status"},
                    "start_time": {"$first": "$start_time"},
                    "end_time": {"$first": "$end_time"},
                    "duration_seconds": {"$first": "$duration_seconds"},
                    "error_msg": {"$first": "$error_msg"},
                }
            },
        ]

        results = self.collection.aggregate(pipeline)

        status_dict = {}
        for r in results:
            agent_name = r["_id"]
            status_dict[agent_name] = {
                "status": r.get("status"),
                "start_time": r.get("start_time").isoformat() if r.get("start_time") else None,
                "end_time": r.get("end_time").isoformat() if r.get("end_time") else None,
                "duration_seconds": r.get("duration_seconds"),
                "error_msg": r.get("error_msg"),
            }

        return status_dict

    def get_observability_snapshot(self, user_email: str, *, limit: int = 25) -> dict:
        """Return tenant-scoped FinOps trace totals, happenings, and circuit-breaker trip count."""
        from src.utils.monitoring import fetch_recent_happenings, fetch_recent_traces

        traces = fetch_recent_traces(self.db, user_email, limit=limit)
        happenings = fetch_recent_happenings(self.db, user_email, limit=limit)
        total_tokens = sum(int(t.get("token_usage", 0) or 0) for t in traces)
        trips = sum(1 for h in happenings if h.get("event") == "circuit_breaker_tripped")
        return {
            "user_email": user_email,
            "trace_count": len(traces),
            "happening_count": len(happenings),
            "recent_tokens_spent": total_tokens,
            "circuit_breaker_trips": trips,
            "traces": traces,
            "happenings": happenings,
        }
