"""
Tests for the CDC Event Publisher.

Validates Redis publish behavior including serialization,
graceful degradation when Redis is unavailable, and stream formatting.
"""
import json
import os
import sys
from unittest.mock import patch, MagicMock


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.events.publisher import (
    publish_journal_event,
    ensure_consumer_group,
    STREAM_KEY,
    CONSUMER_GROUP,
)


class TestPublishJournalEvent:
    """Tests for the publish_journal_event function."""

    @patch("src.events.publisher._get_redis")
    def test_publish_success(self, mock_get_redis):
        """Verify events are published to the correct stream with proper fields."""
        mock_client = MagicMock()
        mock_client.xadd.return_value = "1234567890-0"
        mock_get_redis.return_value = mock_client

        result = publish_journal_event(
            correlation_id="log-W27-2026-07-05-morning-Hero",
            entry_type="log",
            payload={"intention": "Work hard", "actual": "Worked hard"},
            user_id="Hero",
        )

        assert result is True
        mock_client.xadd.assert_called_once()
        call_args = mock_client.xadd.call_args
        assert call_args[0][0] == STREAM_KEY
        event_data = call_args[0][1]
        assert event_data["correlation_id"] == "log-W27-2026-07-05-morning-Hero"
        assert event_data["entry_type"] == "log"
        assert event_data["user_id"] == "Hero"
        # Payload should be JSON-serialized
        payload = json.loads(event_data["payload"])
        assert payload["intention"] == "Work hard"

    @patch("src.events.publisher._get_redis")
    def test_publish_graceful_degradation_when_redis_unavailable(self, mock_get_redis):
        """Verify publish returns False without raising when Redis is down."""
        mock_get_redis.return_value = None

        result = publish_journal_event(
            correlation_id="test-id",
            entry_type="log",
            payload={"intention": "test"},
            user_id="Hero",
        )

        assert result is False

    @patch("src.events.publisher._get_redis")
    def test_publish_handles_xadd_exception(self, mock_get_redis):
        """Verify publish catches Redis exceptions without crashing."""
        mock_client = MagicMock()
        mock_client.xadd.side_effect = ConnectionError("Redis connection lost")
        mock_get_redis.return_value = mock_client

        result = publish_journal_event(
            correlation_id="test-id",
            entry_type="freeform",
            payload={"text": "hello"},
            user_id="Hero",
        )

        assert result is False

    @patch("src.events.publisher._get_redis")
    def test_publish_serializes_datetime_in_payload(self, mock_get_redis):
        """Verify datetimes in payload are serialized via default=str."""
        from datetime import datetime

        mock_client = MagicMock()
        mock_client.xadd.return_value = "1234567890-0"
        mock_get_redis.return_value = mock_client

        result = publish_journal_event(
            correlation_id="test-datetime",
            entry_type="log",
            payload={"processed_at": datetime(2026, 7, 5, 12, 0, 0)},
            user_id="Hero",
        )

        assert result is True
        event_data = mock_client.xadd.call_args[0][1]
        payload = json.loads(event_data["payload"])
        assert "2026-07-05" in payload["processed_at"]


class TestEnsureConsumerGroup:
    """Tests for consumer group management."""

    @patch("src.events.publisher._get_redis")
    def test_create_new_group(self, mock_get_redis):
        """Verify a new consumer group is created successfully."""
        mock_client = MagicMock()
        mock_get_redis.return_value = mock_client

        result = ensure_consumer_group()

        assert result is True
        mock_client.xgroup_create.assert_called_once_with(
            STREAM_KEY, CONSUMER_GROUP, id="0", mkstream=True
        )

    @patch("src.events.publisher._get_redis")
    def test_existing_group_busygroup(self, mock_get_redis):
        """Verify BUSYGROUP error is handled gracefully (group already exists)."""
        mock_client = MagicMock()
        mock_client.xgroup_create.side_effect = Exception("BUSYGROUP Consumer Group name already exists")
        mock_get_redis.return_value = mock_client

        result = ensure_consumer_group()

        assert result is True

    @patch("src.events.publisher._get_redis")
    def test_no_redis_returns_false(self, mock_get_redis):
        """Verify returns False when Redis is unavailable."""
        mock_get_redis.return_value = None

        result = ensure_consumer_group()

        assert result is False


class TestWorkerProcessing:
    """Tests for CDC worker event processing."""

    def test_process_event_routes_correctly(self):
        """Verify events are routed to the correct worker based on entry_type."""
        from src.events.workers import process_event

        with patch("src.events.workers.process_vector_embed") as mock_embed:
            mock_embed.return_value = True
            result = process_event({
                "correlation_id": "log-W27-test",
                "entry_type": "log",
                "user_id": "Hero",
                "payload": json.dumps({"intention": "Test", "actual": "Testing"}),
            })
            assert result is True
            mock_embed.assert_called_once()

    def test_process_event_handles_invalid_json(self):
        """Verify graceful handling of malformed JSON payloads."""
        from src.events.workers import process_event

        with patch("src.events.workers.process_vector_embed") as mock_embed:
            result = process_event({
                "correlation_id": "test-bad-json",
                "entry_type": "log",
                "user_id": "Hero",
                "payload": "NOT VALID JSON {{{",
            })
            assert result is False
            mock_embed.assert_not_called()
