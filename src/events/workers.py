"""
CDC Workers — Consume events from Redis Streams and propagate to downstream systems.

Worker A: VectorDB Embedding (Phase B initial scope)
  - Chunks text from journal entries
  - Embeds via BGE-M3
  - Stores to ChromaDB with correlation_id metadata

Worker B: (Future) Neo4j writes when sync cutover is enabled

Usage:
    python -m src.events.workers          # Run as module
    docker compose up porter-workers      # Run in container

Consumer Group: porter-workers
Stream: stream:journal_events
"""
import json
import logging
import os
import signal
import sys
import time
from typing import Dict, Any

# Ensure project root on path when run as standalone
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.utils.logging_config import setup_logger

logger = setup_logger("cdc_workers")

# Worker configuration
CONSUMER_NAME = os.getenv("WORKER_ID", f"worker-{os.getpid()}")
BATCH_SIZE = 10
BLOCK_MS = 5000  # 5 seconds — blocks waiting for new messages
IDLE_SLEEP = 1   # seconds between empty reads

# Graceful shutdown flag
_shutdown = False


def _handle_signal(signum, frame):
    """Handle SIGTERM/SIGINT for graceful shutdown."""
    global _shutdown
    logger.info(f"[CDC Worker] Received signal {signum}, initiating graceful shutdown...")
    _shutdown = True


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


def process_vector_embed(correlation_id: str, entry_type: str, payload: Dict[str, Any], user_id: str) -> bool:
    """
    Worker A: Embed journal text into ChromaDB with correlation_id metadata.
    
    Args:
        correlation_id: Cross-system lineage ID.
        entry_type: 'log', 'freeform', or 'weekly'.
        payload: Deserialized journal data.
        user_id: Owner of the entry.
        
    Returns:
        True if embedding succeeded, False otherwise.
    """
    try:
        from src.database.vector_database.chromadb_client import ChromaExperimentalClient

        # Extract text based on entry type
        if entry_type == "log":
            text = f"Intention: {payload.get('intention', '')}. Actual: {payload.get('actual', '')}"
            pillar = payload.get("category", "General")
        elif entry_type == "freeform":
            text = payload.get("text", "")
            pillar = "Freeform"
        elif entry_type == "weekly":
            text = payload.get("expectation_text", "")
            pillar = "Weekly Planning"
        else:
            logger.warning(f"[CDC Worker] Unknown entry_type '{entry_type}' for {correlation_id}")
            return False

        if not text or len(text.strip()) < 5:
            logger.info(f"[CDC Worker] Skipping empty text for {correlation_id}")
            return True  # Not an error, just nothing to embed

        # Embed using BGE-M3
        from src.database.vector_database.embedding_client import BGEM3EmbeddingsClient
        emb_client = BGEM3EmbeddingsClient()
        embedding = emb_client.get_embedding(text)

        if not embedding:
            logger.error(f"[CDC Worker] Failed to generate embedding for {correlation_id}")
            return False

        # Store in ChromaDB with correlation_id metadata
        chroma = ChromaExperimentalClient()
        chroma.insert_batch([{
            "text": text,
            "pillar": pillar,
            "embedding": embedding,
            "correlation_id": correlation_id
        }])

        logger.info(f"[CDC Worker] ✅ Embedded {correlation_id} ({entry_type}) -> ChromaDB [{len(text)} chars]")
        return True

    except Exception as e:
        logger.error(f"[CDC Worker] ❌ Embedding failed for {correlation_id}: {e}", exc_info=True)
        return False


def process_event(event_data: Dict[str, str]) -> bool:
    """
    Route an event to the appropriate worker based on its type.
    
    Args:
        event_data: Raw Redis stream message fields.
        
    Returns:
        True if processing succeeded (message should be ACKed).
    """
    correlation_id = event_data.get("correlation_id", "unknown")
    entry_type = event_data.get("entry_type", "unknown")
    user_id = event_data.get("user_id", "Hero")

    try:
        payload = json.loads(event_data.get("payload", "{}"))
    except json.JSONDecodeError as e:
        logger.error(f"[CDC Worker] Invalid JSON payload for {correlation_id}: {e}")
        return False

    logger.info(f"[CDC Worker] Processing [CID:{correlation_id}] type={entry_type} user={user_id}")

    # Worker A: Vector embedding
    embed_ok = process_vector_embed(correlation_id, entry_type, payload, user_id)

    # Worker B: (Future) Neo4j write — currently handled synchronously in routes
    # neo4j_ok = process_neo4j_write(correlation_id, entry_type, payload, user_id)

    return embed_ok


def run_consumer():
    """
    Main consumer loop — reads from Redis Stream using XREADGROUP.
    Implements exactly-once semantics via consumer groups + ACK.
    """
    from src.events.publisher import _get_redis, STREAM_KEY, CONSUMER_GROUP, ensure_consumer_group

    client = _get_redis()
    if client is None:
        logger.error("[CDC Worker] Cannot start — Redis is unavailable.")
        sys.exit(1)

    # Ensure consumer group exists
    if not ensure_consumer_group():
        logger.error("[CDC Worker] Cannot create consumer group. Exiting.")
        sys.exit(1)

    logger.info(f"[CDC Worker] Started consumer '{CONSUMER_NAME}' on group '{CONSUMER_GROUP}'")
    logger.info(f"[CDC Worker] Listening on stream '{STREAM_KEY}'...")

    consecutive_errors = 0
    max_consecutive_errors = 10

    while not _shutdown:
        try:
            # Read new messages for this consumer
            messages = client.xreadgroup(
                groupname=CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={STREAM_KEY: ">"},
                count=BATCH_SIZE,
                block=BLOCK_MS
            )

            if not messages:
                continue  # No new messages, loop again

            for stream_name, stream_messages in messages:
                for msg_id, msg_data in stream_messages:
                    try:
                        success = process_event(msg_data)

                        if success:
                            # ACK the message — it won't be redelivered
                            client.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)
                            logger.debug(f"[CDC Worker] ACKed message {msg_id}")
                        else:
                            # Don't ACK — message will be retried via pending entries
                            logger.warning(f"[CDC Worker] Processing failed for {msg_id}, will retry")

                    except Exception as e:
                        logger.error(f"[CDC Worker] Error processing message {msg_id}: {e}", exc_info=True)

            consecutive_errors = 0  # Reset on successful batch

        except KeyboardInterrupt:
            logger.info("[CDC Worker] KeyboardInterrupt received, shutting down...")
            break
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"[CDC Worker] Consumer loop error ({consecutive_errors}/{max_consecutive_errors}): {e}")

            if consecutive_errors >= max_consecutive_errors:
                logger.critical("[CDC Worker] Too many consecutive errors. Shutting down.")
                break

            time.sleep(min(consecutive_errors * 2, 30))  # Backoff

    logger.info("[CDC Worker] Consumer shut down gracefully.")


if __name__ == "__main__":
    run_consumer()
