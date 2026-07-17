"""
Correlation ID Generator for Cross-System Data Lineage.

Generates deterministic, human-readable IDs that track data records
across Mongo → Neo4j → Vector DB → Agent output.

Format:
    log-W27-2026-07-01-morning-Hero
    freeform-W27-2026-07-05-14:30:22-Hero
    weekly-W27-2026-06-29-Hero
    reflection-W27-2026-07-01-Hero

Why deterministic (not UUID): same inputs always produce the same ID,
making debugging in MongoDB shell or Neo4j browser trivial — you can
visually trace a record by reading its ID.
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def generate_correlation_id(
    user_id: str,
    day_str: str,
    time_chunk: str = None,
    entry_type: str = "log",
) -> str:
    """
    Generates a deterministic, human-readable correlation ID.

    Args:
        user_id: The username or identifier (e.g., "Hero").
        day_str: Date string in "YYYY-MM-DD" format.
        time_chunk: Optional time chunk ID (e.g., "morning", "evening").
                    For freeform entries, pass an HH:MM:SS timestamp instead.
        entry_type: One of "log", "freeform", "weekly", "reflection".

    Returns:
        A correlation ID string.

    Examples:
        >>> generate_correlation_id("Hero", "2026-07-01", "morning", "log")
        'log-W27-2026-07-01-morning-Hero'
        >>> generate_correlation_id("Hero", "2026-07-05", "14:30:22", "freeform")
        'freeform-W27-2026-07-05-14:30:22-Hero'
        >>> generate_correlation_id("Hero", "2026-06-29", entry_type="weekly")
        'weekly-W26-2026-06-29-Hero'
    """
    if not user_id or not day_str:
        logger.warning(
            f"Cannot generate correlation ID: user_id='{user_id}', day_str='{day_str}'"
        )
        return f"{entry_type}-UNKNOWN-{user_id or 'anonymous'}"

    # Derive ISO week number from the date string
    try:
        dt = datetime.strptime(day_str, "%Y-%m-%d")
        _iso_year, iso_week, _iso_weekday = dt.isocalendar()
        week_label = f"W{iso_week:02d}"
    except ValueError:
        logger.warning(f"Invalid date format for correlation ID: '{day_str}'")
        week_label = "W00"

    # Build the ID segments
    segments = [entry_type, week_label, day_str]

    if time_chunk:
        segments.append(time_chunk)

    segments.append(user_id)

    return "-".join(segments)


def generate_freeform_correlation_id(
    user_id: str,
    day_str: str,
) -> str:
    """
    Generates a correlation ID for freeform journal entries.
    Includes the current HH:MM:SS timestamp for uniqueness since
    freeform entries don't have a time_chunk.

    Args:
        user_id: The username or identifier.
        day_str: Date string in "YYYY-MM-DD" format.

    Returns:
        A correlation ID string with HH:MM:SS granularity.
    """
    now_utc = datetime.now(timezone.utc)
    time_stamp = now_utc.strftime("%H:%M:%S")
    return generate_correlation_id(
        user_id=user_id,
        day_str=day_str,
        time_chunk=time_stamp,
        entry_type="freeform",
    )
