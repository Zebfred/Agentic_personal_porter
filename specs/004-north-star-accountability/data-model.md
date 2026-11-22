# Data Model: North Star Accountability & Weekly Streak Engine (`004-north-star-accountability`)

**Feature Branch**: `feat/004-north-star-accountability`
**Schema Module**: `src/schemas/accountability_models.py`

---

## 1. Pydantic v2 Boundary Contracts (`src/schemas/accountability_models.py`)

### 1.1 `PillarCategory` & `StreakStatus` (Literals)

* `PillarCategory`: `"career_fundamentals" | "business_finops" | "builder_joy_fuel" | "life_relationship" | "health_energy"`
* `StreakStatus`: `"active" | "at_risk" | "paused_grace" | "broken"`

### 1.2 `NorthStarPillar`

* `pillar_id`: `str` (`^[a-z0-9][a-z0-9_-]{1,63}$`) — Stable slug (e.g., `cpp-airgap-drills`, `protected-family-time`).
* `title`: `str` (`min_length=2`, `max_length=100`).
* `category`: `PillarCategory`.
* `weekly_target_count`: `int` (`ge=1`, `le=21`) — Weekly micro-win count target.
* `target_unit`: `str` (`max_length=40`, default `"sessions"`).
* `is_restorative_life_pillar`: `bool` (default `False`) — When `True`, check-ins boost `life_harmony_ratio` and are never penalized during vacation.
* `grace_eligible`: `bool` (default `True`) — Freezes streak during declared Grace/Vacation ISO weeks.
* `active`: `bool` (default `True`).

### 1.3 `ReconCheckInRequest` & `ReconCheckInRecord`

* `pillar_id`: `str` — Must match an active tenant pillar.
* `iso_date`: `str` (`^\d{4}-\d{2}-\d{2}$`) — Local date of the win.
* `minutes_spent`: `int` (`ge=1`, `le=1440`) — Duration logged.
* `win_note`: `str` (`max_length=500`, default `""`) — Short reflection or concrete artifact link.
* `idempotency_key`: `str` (`min_length=4`, `max_length=128`) — Prevents mobile double-tap duplicates.
* `source`: `Literal["hub_recon", "calendar_sync", "cli_export", "mobile_quick"]` (default `"hub_recon"`).

### 1.4 `PillarStreakSummary` & `AccountabilityDashboardResponse`

* `PillarStreakSummary`: `pillar_id`, `title`, `category`, `is_restorative_life_pillar`, `completed_this_week`, `weekly_target_count`, `completion_ratio` (`0.0..1.0` clamped for display + raw ratio), `current_streak_weeks`, `longest_streak_weeks`, `streak_status`.
* `AccountabilityDashboardResponse`: `user_email`, `iso_week`, `grace_mode_active`, `life_harmony_ratio`, `overall_completion_ratio`, `pillars: list[PillarStreakSummary]`.

---

## 2. MongoDB Collections & Compound Indexes

| Collection Constant | Collection Name | Indexes | Projection |
| :--- | :--- | :--- | :--- |
| `NORTH_STAR_PILLARS_COLLECTION` | `"north_star_pillars"` | `(user_email, pillar_id)` UNIQUE, `(user_email, active)` | `{"_id": 0, "user_email": 1, "pillar_id": 1, "title": 1, "category": 1, "weekly_target_count": 1, "target_unit": 1, "is_restorative_life_pillar": 1, "grace_eligible": 1, "active": 1}` |
| `PILLAR_CHECKINS_COLLECTION` | `"pillar_checkins"` | `(user_email, idempotency_key)` UNIQUE, `(user_email, iso_week -1, pillar_id)` | `{"_id": 0, "checkin_uuid": 1, "user_email": 1, "pillar_id": 1, "iso_date": 1, "iso_week": 1, "minutes_spent": 1, "win_note": 1, "source": 1}` |
| `GRACE_WINDOWS_COLLECTION` | `"accountability_grace_windows"` | `(user_email, iso_week)` UNIQUE | `{"_id": 0, "user_email": 1, "iso_week": 1, "reason": 1, "enabled": 1}` |

---

## 3. Neo4j Identity Graph Extension

```cypher
MERGE (h:Hero {email: $user_email})
MERGE (p:NorthStarPillar {tenant_pillar_key: $user_email + "::" + $pillar_id})
  SET p.pillar_id = $pillar_id,
      p.title = $title,
      p.category = $category,
      p.is_restorative_life_pillar = $is_restorative_life_pillar
MERGE (h)-[:PURSUES]->(p)
MERGE (c:PillarCheckIn {checkin_uuid: $checkin_uuid})
  SET c.iso_date = $iso_date,
      c.iso_week = $iso_week,
      c.minutes_spent = $minutes_spent,
      c.win_note = $win_note
MERGE (h)-[:LOGGED_WIN]->(c)
MERGE (c)-[:ADVANCES]->(p)
```
