import pytest
from pydantic import ValidationError
from src.schemas.api_models import JournalLogBase, JournalRequestSchema, CalendarRequestSchema

def test_valid_journal_request():
    payload = {
        "journal_entry": "Today was productive.",
        "log_data": {
            "day": "Monday",
            "timeChunk": "Morning",
            "intention": "Work hard",
            "actual": "Worked hard",
            "feeling": "Good",
            "brainFog": 1,
            "isValuableDetour": False,
            "inventoryNote": "Learned a lot"
        }
    }
    schema = JournalRequestSchema(**payload)
    assert schema.journal_entry == "Today was productive."
    assert schema.log_data.day == "Monday"

def test_invalid_journal_request_missing_fields():
    payload = {
        "journal_entry": "Missing log data entirely"
    }
    with pytest.raises(ValidationError):
        JournalRequestSchema(**payload)

def test_valid_calendar_request():
    req = CalendarRequestSchema(date="2026-03-20")
    assert req.date == "2026-03-20"

def test_empty_calendar_request():
    req = CalendarRequestSchema()
    assert req.date is None
