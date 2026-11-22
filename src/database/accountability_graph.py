"""Optional idempotent Neo4j sync helper for North Star Accountability (004)."""

import logging
from typing import Any

from src.config import NeoConfig

logger = logging.getLogger("APP_ROUTER")

_MERGE_WIN_CYPHER = (
    "MERGE (h:Hero {email: $user_email}) "
    "MERGE (p:NorthStarPillar {tenant_pillar_key: $tenant_key}) "
    "SET p.pillar_id = $pillar_id, p.title = $title, p.category = $category, "
    "    p.is_restorative_life_pillar = $is_restorative "
    "MERGE (h)-[:PURSUES]->(p) "
    "MERGE (w:PillarWin {entry_uuid: $entry_uuid}) "
    "SET w.iso_date = $iso_date, w.iso_week = $iso_week, "
    "    w.minutes_spent = $minutes_spent, w.win_note = $win_note "
    "MERGE (h)-[:LOGGED_WIN]->(w) MERGE (w)-[:ADVANCES]->(p)"
)


def sync_pillar_win_to_graph(
    user_email: str, pillar: dict[str, Any], record: dict[str, Any]
) -> str:
    """Idempotently MERGE a pillar win into Neo4j if configured; fail gracefully offline."""
    if not (NeoConfig.NEO4J_URI and NeoConfig.NEO4J_USER and NeoConfig.NEO4J_PASS):
        return "PENDING_GRAPH_SYNC"
    try:
        from src.database.neo4j_client import Neo4jClient

        Neo4jClient().execute_write(
            _MERGE_WIN_CYPHER,
            {
                "user_email": user_email,
                "tenant_key": f"{user_email}::{pillar['pillar_id']}",
                "pillar_id": pillar["pillar_id"],
                "title": pillar["title"],
                "category": pillar["category"],
                "is_restorative": bool(pillar.get("is_restorative_life_pillar", False)),
                "entry_uuid": record["entry_uuid"],
                "iso_date": record["iso_date"],
                "iso_week": record["iso_week"],
                "minutes_spent": record["minutes_spent"],
                "win_note": record["win_note"],
            },
        )
        return "GRAPH_SYNCED"
    except Exception as exc:
        logger.warning("Neo4j accountability sync deferred: %s", exc)
        return "PENDING_GRAPH_SYNC"
