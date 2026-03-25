import uuid
from typing import Dict, Any

class UUIDGenerator:
    """
    Handles deterministic UUID generation so that a specific Google Calendar Event
    always produces the same UUID across different collections if re-processed.
    """
    # A base UUID namespace for Google Calendar events
    NAMESPACE_GCAL = uuid.UUID('2db0f24e-4e4b-4b20-9428-fb48722a2105')

    @classmethod
    def generate_for_event(cls, gcal_id: str) -> str:
        """
        Generates a deterministic UUID based on the Google Calendar ID.
        """
        return str(uuid.uuid5(cls.NAMESPACE_GCAL, gcal_id))
