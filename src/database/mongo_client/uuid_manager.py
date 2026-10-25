import uuid


class UUIDGenerator:
    """
    Handles deterministic UUID generation so that a specific Google Calendar Event
    always produces the same UUID across different collections if re-processed.
    """

    # A base UUID namespace for Google Calendar events
    NAMESPACE_GCAL = uuid.UUID("2db0f24e-4e4b-4b20-9428-fb48722a2105")
    # A base UUID namespace for Atlassian Jira issues and Jules work orders
    NAMESPACE_JIRA = uuid.UUID("8f14e45f-ceea-467a-9a38-7f6544e2b319")

    @classmethod
    def generate_for_event(cls, gcal_id: str, user_email: str) -> str:
        """
        Generates a deterministic UUID based on the User Email and Google Calendar ID.
        """
        combined_string = f"{user_email}::{gcal_id}"
        return str(uuid.uuid5(cls.NAMESPACE_GCAL, combined_string))

    @classmethod
    def generate_for_jira_issue(cls, jira_key: str, user_email: str) -> str:
        """
        Generates a deterministic UUID based on the User Email and Jira issue key.
        Prevents cross-tenant collisions and guarantees idempotent upserts across syncs.
        """
        combined_string = f"{user_email}::jira::{jira_key}"
        return str(uuid.uuid5(cls.NAMESPACE_JIRA, combined_string))
