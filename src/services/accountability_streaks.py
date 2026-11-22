"""Pure deterministic ISO-week streak math & starter templates (004)."""

from datetime import date, datetime, timedelta, timezone
from typing import Any

from src.schemas.accountability_models import PillarStreakSummary, StreakStatus

STARTER_PILLARS: list[dict[str, Any]] = [
    {
        "pillar_id": "cpp-airgap-drills",
        "title": "C++ Air-Gapped Fundamentals",
        "category": "career_fundamentals",
        "weekly_target_count": 4,
        "target_unit": "25m drills",
        "is_restorative_life_pillar": False,
        "grace_eligible": True,
        "active": True,
    },
    {
        "pillar_id": "business-finops",
        "title": "Business & FinOps Hygiene",
        "category": "business_finops",
        "weekly_target_count": 2,
        "target_unit": "blocks",
        "is_restorative_life_pillar": False,
        "grace_eligible": True,
        "active": True,
    },
    {
        "pillar_id": "builder-joy-fuel",
        "title": "Builder Joy Fuel (RL & Swarm Defense)",
        "category": "builder_joy_fuel",
        "weekly_target_count": 2,
        "target_unit": "sessions",
        "is_restorative_life_pillar": False,
        "grace_eligible": True,
        "active": True,
    },
    {
        "pillar_id": "protected-family-time",
        "title": "Protected Life & Relationship Time",
        "category": "life_relationship",
        "weekly_target_count": 3,
        "target_unit": "unplugged moments",
        "is_restorative_life_pillar": True,
        "grace_eligible": True,
        "active": True,
    },
]


def current_iso_week() -> str:
    """Return the current UTC ISO week string (YYYY-Www)."""
    iso_year, iso_wk, _ = datetime.now(timezone.utc).date().isocalendar()
    return f"{iso_year:04d}-W{iso_wk:02d}"


def _parse_iso_week_monday(iso_week: str) -> date:
    year_str, week_str = iso_week.split("-W")
    return date.fromisocalendar(int(year_str), int(week_str), 1)


def _format_iso_week(day: date) -> str:
    iso_year, iso_wk, _ = day.isocalendar()
    return f"{iso_year:04d}-W{iso_wk:02d}"


def _active_streak_weeks(
    counts: dict[str, int],
    grace_weeks: set[str],
    target_week: str,
    target_count: int,
    grace_ok: bool,
) -> int:
    """Walk backward from target_week counting active streak weeks (grace pauses cleanly)."""
    streak = 0
    cursor = _parse_iso_week_monday(target_week)
    for offset in range(52):
        wk = _format_iso_week(cursor - timedelta(weeks=offset))
        if counts.get(wk, 0) >= target_count:
            streak += 1
        elif (wk in grace_weeks and grace_ok) or offset == 0:
            continue
        else:
            break
    return streak


def _longest_streak_weeks(
    counts: dict[str, int],
    grace_weeks: set[str],
    target_week: str,
    target_count: int,
    grace_ok: bool,
) -> int:
    """Scan observed weeks chronologically to determine longest unbroken streak."""
    longest, running, prev_monday = 0, 0, None
    for wk in sorted(set(counts.keys()) | grace_weeks | {target_week}):
        wk_monday = _parse_iso_week_monday(wk)
        if prev_monday is not None and (wk_monday - prev_monday).days > 7:
            running = 0
        if counts.get(wk, 0) >= target_count:
            running += 1
            longest = max(longest, running)
        elif not (wk in grace_weeks and grace_ok):
            running = 0
        prev_monday = wk_monday
    return longest


def compute_pillar_streak(
    pillar: dict[str, Any],
    counts: dict[str, int],
    grace_weeks: set[str],
    target_week: str,
) -> PillarStreakSummary:
    """Deterministically compute streak metrics & status for one North Star pillar."""
    target_count = int(pillar["weekly_target_count"])
    completed_now = counts.get(target_week, 0)
    grace_ok = bool(pillar.get("grace_eligible", True))
    is_restorative = bool(pillar.get("is_restorative_life_pillar", False))
    current = _active_streak_weeks(counts, grace_weeks, target_week, target_count, grace_ok)
    longest = max(
        current, _longest_streak_weeks(counts, grace_weeks, target_week, target_count, grace_ok)
    )

    if completed_now >= target_count:
        status: StreakStatus = "active"
    elif target_week in grace_weeks and grace_ok and not is_restorative:
        status = "paused_grace"
    elif current > 0 or completed_now > 0:
        status = "at_risk"
    else:
        status = "broken"

    return PillarStreakSummary(
        pillar_id=str(pillar["pillar_id"]),
        title=str(pillar["title"]),
        category=pillar["category"],
        is_restorative_life_pillar=is_restorative,
        completed_this_week=completed_now,
        weekly_target_count=target_count,
        completion_ratio=min(1.0, round(completed_now / max(1, target_count), 4)),
        current_streak_weeks=current,
        longest_streak_weeks=longest,
        streak_status=status,
    )
