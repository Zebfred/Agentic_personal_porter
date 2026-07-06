"""
Tests for the Correlation ID Generator.
Validates deterministic behavior, format correctness, and edge cases.
"""
from unittest.mock import patch
from datetime import datetime, timezone

from src.utils.correlation import generate_correlation_id, generate_freeform_correlation_id


class TestGenerateCorrelationId:
    """Tests for the primary generate_correlation_id function."""

    def test_standard_log_entry(self):
        """Standard time-chunk log should produce the expected format."""
        result = generate_correlation_id("Hero", "2026-07-01", "morning", "log")
        assert result == "log-W27-2026-07-01-morning-Hero"

    def test_deterministic_output(self):
        """Same inputs should always produce the same ID."""
        id_a = generate_correlation_id("Hero", "2026-07-01", "morning", "log")
        id_b = generate_correlation_id("Hero", "2026-07-01", "morning", "log")
        assert id_a == id_b

    def test_weekly_entry_no_time_chunk(self):
        """Weekly entries have no time_chunk, so it should be omitted from the ID."""
        result = generate_correlation_id("Hero", "2026-06-29", entry_type="weekly")
        assert result == "weekly-W27-2026-06-29-Hero"

    def test_reflection_entry(self):
        """Reflection entries should follow the same pattern."""
        result = generate_correlation_id("Hero", "2026-07-05", entry_type="reflection")
        assert result == "reflection-W27-2026-07-05-Hero"

    def test_different_users_produce_different_ids(self):
        """Multi-tenant: different users get different IDs for the same entry."""
        id_hero = generate_correlation_id("Hero", "2026-07-01", "morning", "log")
        id_other = generate_correlation_id("Adventurer", "2026-07-01", "morning", "log")
        assert id_hero != id_other
        assert "Hero" in id_hero
        assert "Adventurer" in id_other

    def test_week_number_calculation(self):
        """Verify ISO week number is correctly derived."""
        # 2026-01-01 is a Thursday, ISO week 1
        result = generate_correlation_id("Hero", "2026-01-01", "morning", "log")
        assert "W01" in result

    def test_freeform_entry_with_timestamp(self):
        """Freeform entries should include HH:MM:SS as the time_chunk."""
        result = generate_correlation_id("Hero", "2026-07-05", "14:30:22", "freeform")
        assert result == "freeform-W27-2026-07-05-14:30:22-Hero"

    def test_invalid_date_falls_back_to_w00(self):
        """Invalid date strings should still produce an ID with W00."""
        result = generate_correlation_id("Hero", "not-a-date", "morning", "log")
        assert "W00" in result
        assert "not-a-date" in result

    def test_missing_user_id(self):
        """Missing user_id should produce a fallback ID."""
        result = generate_correlation_id("", "2026-07-01", "morning", "log")
        assert "UNKNOWN" in result

    def test_missing_day_str(self):
        """Missing day_str should produce a fallback ID."""
        result = generate_correlation_id("Hero", "", "morning", "log")
        assert "UNKNOWN" in result

    def test_all_time_chunks(self):
        """All valid time chunk IDs should produce distinct correlation IDs."""
        chunks = ["late-night", "early-morning", "late-morning", "afternoon", "evening", "early-night"]
        ids = set()
        for chunk in chunks:
            cid = generate_correlation_id("Hero", "2026-07-01", chunk, "log")
            assert chunk in cid
            ids.add(cid)
        # All 6 should be unique
        assert len(ids) == 6


class TestGenerateFreeformCorrelationId:
    """Tests for the freeform-specific helper."""

    @patch("src.utils.correlation.datetime")
    def test_freeform_includes_current_time(self, mock_dt):
        """Freeform helper should use current UTC HH:MM:SS."""
        mock_now = datetime(2026, 7, 5, 14, 30, 22, tzinfo=timezone.utc)
        mock_dt.now.return_value = mock_now
        mock_dt.strptime = datetime.strptime
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)

        result = generate_freeform_correlation_id("Hero", "2026-07-05")
        assert result == "freeform-W27-2026-07-05-14:30:22-Hero"

    def test_freeform_entry_type(self):
        """Freeform correlation IDs should always start with 'freeform-'."""
        result = generate_freeform_correlation_id("Hero", "2026-07-05")
        assert result.startswith("freeform-")

    def test_freeform_contains_user_id(self):
        """Freeform correlation IDs should contain the user ID."""
        result = generate_freeform_correlation_id("TestUser", "2026-07-05")
        assert result.endswith("-TestUser")
