"""
Tenant-Scoped MongoDB and Neo4j Persistence Layer for Jira Issues & Jules Work Orders.

Adheres strictly to:
- Constitution Principle II: Multi-Tenant Partitioning (`user_email` scoping, composite UUIDv5)
- Constitution Principle III & Bolt Playbook:
  - Batched `bulk_write(ops, ordered=False)` instead of iterative network calls
  - Explicit projection dictionaries (`{"_id": 0, ...}`) on all batch queries
  - Config-driven collection names (`MongoConfig.JIRA_STAGING_COLLECTION`)
  - `DESCENDING` (-1) temporal indexes
"""

import logging
from typing import Any, Optional
from pymongo import ASCENDING, DESCENDING, UpdateOne

from src.config import MongoConfig
from src.database.mongo_client.connection import MongoConnectionManager
from src.database.neo4j_client.connection import get_driver
from src.schemas.jira_models import JiraIssueRecord, JulesWorkOrder

logger = logging.getLogger(__name__)


class JiraStorage:
    """
    Manages local MongoDB staging and Neo4j Quest/Intention graph merging
    for synchronized Jira issues and Jules work orders.
    """

    DEDUP_PROJECTION: dict[str, int] = {
        "_id": 0,
        "jira_key": 1,
        "task_id": 1,
        "status": 1,
        "sync_status": 1,
    }

    FULL_RECORD_PROJECTION: dict[str, int] = {
        "_id": 0,
    }

    def __init__(self, db: Any = None) -> None:
        self.db = db if db is not None else MongoConnectionManager.get_db()
        self.jira_col = self.db[MongoConfig.JIRA_STAGING_COLLECTION]
        self.jules_col = self.db[MongoConfig.JULES_WORK_ORDERS_COLLECTION]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """Create config-driven compound indexes with DESCENDING temporal order."""
        self.jira_col.create_index(
            [("user_email", ASCENDING), ("updated_at", DESCENDING)],
            name="idx_jira_user_updated_desc",
        )
        self.jira_col.create_index(
            [("user_email", ASCENDING), ("jira_key", ASCENDING)],
            unique=True,
            name="idx_jira_user_key_unique",
        )
        self.jules_col.create_index(
            [("user_email", ASCENDING), ("work_order_id", ASCENDING)],
            unique=True,
            name="idx_jules_user_order_unique",
        )

    @staticmethod
    def _execute_bulk_write(collection: Any, ops: list[UpdateOne]) -> dict[str, int]:
        """
        Execute `bulk_write(ops, ordered=False)` with transparent compatibility for
        PyMongo 4.11+ `UpdateOne(sort=...)` on `mongomock` collections in unit tests.
        """
        try:
            result = collection.bulk_write(ops, ordered=False)
            return {
                "upserted_count": int(getattr(result, "upserted_count", 0) or 0),
                "modified_count": int(getattr(result, "modified_count", 0) or 0),
            }
        except TypeError as exc:
            if "sort" not in str(exc):
                raise
            upserted = 0
            modified = 0
            for op in ops:
                res = collection.update_one(
                    op._filter,
                    op._doc,
                    upsert=op._upsert,
                )
                if getattr(res, "upserted_id", None) is not None:
                    upserted += 1
                else:
                    modified += int(getattr(res, "modified_count", 0) or 0)
            return {"upserted_count": upserted, "modified_count": modified}

    def bulk_upsert_issues(self, records: list[JiraIssueRecord]) -> dict[str, int]:
        """
        Persist multiple JiraIssueRecord objects in a single batched bulk_write call.
        Never executes update_one inside a loop in production (Principle III.3 / Bolt).
        """
        if not records:
            return {"upserted_count": 0, "modified_count": 0}

        ops: list[UpdateOne] = []
        for record in records:
            payload = record.model_dump()
            ops.append(
                UpdateOne(
                    {
                        "user_email": record.user_email,
                        "jira_key": record.jira_key,
                    },
                    {"$set": payload},
                    upsert=True,
                )
            )

        return self._execute_bulk_write(self.jira_col, ops)

    def get_existing_task_mappings(
        self,
        user_email: str,
        project_key: Optional[str] = None,
    ) -> dict[str, dict[str, Any]]:
        """
        Return a mapping of `task_id -> projected issue metadata` for deduplicating
        Spec-Kit tasks (`T001`+) using explicit field projections (Bolt compliance).
        """
        query: dict[str, Any] = {"user_email": user_email}
        if project_key:
            query["project_key"] = project_key

        cursor = self.jira_col.find(query, self.DEDUP_PROJECTION)
        docs = list(cursor)
        mapping: dict[str, dict[str, Any]] = {}
        for doc in docs:
            task_id = doc.get("task_id")
            if task_id:
                mapping[str(task_id)] = doc
        return mapping

    def get_issue_by_key(
        self,
        user_email: str,
        jira_key: str,
    ) -> Optional[JiraIssueRecord]:
        """Fetch a single tenant-scoped JiraIssueRecord by its Jira key."""
        doc = self.jira_col.find_one(
            {"user_email": user_email, "jira_key": jira_key},
            self.FULL_RECORD_PROJECTION,
        )
        if not doc:
            return None
        return JiraIssueRecord.model_validate(doc)

    def get_pending_upstream_issues(
        self,
        user_email: str,
        project_key: Optional[str] = None,
    ) -> list[JiraIssueRecord]:
        """
        Retrieve issues queued locally with `sync_status='pending_upstream'`
        for eventual consistency flushing when Jira returns online.
        """
        query: dict[str, Any] = {
            "user_email": user_email,
            "sync_status": "pending_upstream",
        }
        if project_key:
            query["project_key"] = project_key

        docs = list(
            self.jira_col.find(query, self.FULL_RECORD_PROJECTION).sort("updated_at", DESCENDING)
        )
        return [JiraIssueRecord.model_validate(doc) for doc in docs]

    def save_work_order(self, work_order: JulesWorkOrder) -> dict[str, int]:
        """Persist a JulesWorkOrder idempotently using bulk_write."""
        payload = work_order.model_dump()
        ops = [
            UpdateOne(
                {
                    "user_email": work_order.user_email,
                    "work_order_id": work_order.work_order_id,
                },
                {"$set": payload},
                upsert=True,
            )
        ]
        return self._execute_bulk_write(self.jules_col, ops)

    def merge_issues_to_neo4j(self, records: list[JiraIssueRecord]) -> int:
        """
        Idempotently merge JiraIssueRecord items into the Neo4j Identity Graph
        as `(:Hero)-[:PURSUES_QUEST]->(:Quest:Intention)` nodes.
        Uses singleton driver pooling (Principle III.1).
        """
        if not records:
            return 0

        cypher = """
        UNWIND $batch AS item
        MERGE (h:Hero {user_email: item.user_email})
        MERGE (q:Quest:Intention {uuid: item.uuid, user_email: item.user_email})
        SET q.jira_key = item.jira_key,
            q.project_key = item.project_key,
            q.task_id = item.task_id,
            q.summary = item.summary,
            q.status = item.status,
            q.persona = item.persona,
            q.correlation_id = item.correlation_id,
            q.updated_at = item.updated_at
        MERGE (h)-[:PURSUES_QUEST]->(q)
        """
        batch_payload = [r.model_dump() for r in records]
        try:
            driver = get_driver()
            with driver.session() as session:
                session.execute_write(lambda tx: tx.run(cypher, batch=batch_payload))
            return len(batch_payload)
        except Exception as exc:
            logger.warning(
                "Neo4j Quest merge deferred (local MongoDB remains authoritative): %s",
                exc,
            )
            return 0
