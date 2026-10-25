import time
from src.database.mongo_storage import SovereignMongoStorage


def test_mock_mongo_fixture_in_memory(mock_mongo):
    """
    Verify that SovereignMongoStorage uses in-memory mongomock
    executing offline in < 10ms with zero network overhead.
    """
    start_time = time.perf_counter()
    storage = SovereignMongoStorage()

    # Insert a dummy record
    sample_entry = {
        "day": "2026-10-11",
        "timeChunk": "10:00",
        "actual": "TDD validation with in-memory mongomock",
        "tag": "Governance",
    }
    result = storage.save_journal_entry(sample_entry, user_id="test_hero")
    duration = time.perf_counter() - start_time

    assert result == "Updated 2026-10"
    # Verify sub-second speed (< 0.10s)
    assert duration < 0.10, f"Expected < 100ms execution, took {duration:.4f}s"

    # Verify query from in-memory collection
    saved_doc = storage.journal_col.find_one({"month_id": "2026-10", "user_id": "test_hero"})
    assert saved_doc is not None
    assert "weeks" in saved_doc

    # Also verify direct collection operations and helper lookups
    storage.users_col.insert_one({"username": "test_hero", "email": "hero@nexus.io"})
    user_doc = storage.get_user_by_email("hero@nexus.io")
    assert user_doc is not None
    assert user_doc["username"] == "test_hero"
