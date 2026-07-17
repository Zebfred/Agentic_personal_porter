"""
Event Publisher — Publishes journal events to Redis Streams for CDC workers.

Events are published after the primary Mongo write succeeds. If Redis is
unavailable, the publish is logged as a warning but does NOT block the
user-facing response (graceful degradation).

Stream: stream:journal_events
Consumer Group: porter-workers
"""
import json
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Lazy-init Redis client to avoid import-time connection failures
_redis_client = None


def _get_redis() -> Optional[Any]:
    """
    Lazily initialize and return a Redis client.
    Returns None if redis is not available.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        logger.info("[CDC] REDIS_URL not set — event publishing disabled.")
        return None

    try:
        import redis
        _redis_client = redis.StrictRedis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3
        )
        # Verify connectivity
        _redis_client.ping()
        logger.info(f"[CDC] Redis connected at {redis_url}")
        return _redis_client
    except Exception as e:
        logger.warning(f"[CDC] Redis unavailable ({e}) — events will not be published.")
        _redis_client = None
        return None


# Stream and consumer group constants
STREAM_KEY = "stream:journal_events"
CONSUMER_GROUP = "porter-workers"


def publish_journal_event(
    correlation_id: str,
    entry_type: str,
    payload: Dict[str, Any],
    user_id: str = "Hero"
) -> bool:
    """
    Publish a journal event to the Redis Stream for async CDC processing.

    Args:
        correlation_id: The cross-system lineage ID.
        entry_type: One of 'log', 'freeform', 'weekly'.
        payload: The journal data to be processed by workers.
        user_id: The user who created the entry.

    Returns:
        True if published successfully, False otherwise.
    """
    client = _get_redis()
    if client is None:
        return False

    try:
        # Serialize payload — Redis streams only accept flat string fields
        event = {
            "correlation_id": correlation_id,
            "entry_type": entry_type,
            "user_id": user_id,
            "payload": json.dumps(payload, default=str),
        }

        # XADD to the stream. Redis auto-generates the message ID.
        msg_id = client.xadd(STREAM_KEY, event)
        logger.info(f"[CDC] Published event {msg_id} to {STREAM_KEY} "
                     f"[CID:{correlation_id}] type={entry_type}")
        return True

    except Exception as e:
        logger.warning(f"[CDC] Failed to publish event for {correlation_id}: {e}")
        return False


def ensure_consumer_group() -> bool:
    """
    Create the consumer group if it doesn't exist.
    Called by workers on startup.
    """
    client = _get_redis()
    if client is None:
        return False

    try:
        client.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True)
        logger.info(f"[CDC] Created consumer group '{CONSUMER_GROUP}' on '{STREAM_KEY}'")
        return True
    except Exception as e:
        # BUSYGROUP means group already exists — that's fine
        if "BUSYGROUP" in str(e):
            logger.debug(f"[CDC] Consumer group '{CONSUMER_GROUP}' already exists.")
            return True
        logger.error(f"[CDC] Failed to create consumer group: {e}")
        return False
