# API Contracts: North Star Accountability (`004-north-star-accountability`)

All endpoints require a valid JWT (`Authorization: Bearer <token>`) and scope all reads/writes exclusively to `request.user_email`.

---

## 1. `GET /api/accountability/pillars`

Returns active North Star Pillars for the authenticated Hero (or starter template metadata when empty).

```json
{
  "status": "success",
  "user_email": "hero@example.com",
  "pillars": [
    {
      "pillar_id": "cpp-airgap-drills",
      "title": "C++ Air-Gapped Fundamentals",
      "category": "career_fundamentals",
      "weekly_target_count": 4,
      "target_unit": "25m drills",
      "is_restorative_life_pillar": false,
      "grace_eligible": true,
      "active": true
    }
  ]
}
```

---

## 2. `PUT /api/accountability/pillars`

Upserts up to 6 North Star Pillars atomically via MongoDB `bulk_write` and idempotent Neo4j `MERGE`.

* **Request Body:** `PillarUpsertBatchRequest` (`pillars: list[NorthStarPillar]`, max length `6`).
* **Responses:** `200 OK` with persisted pillar count; `422 Unprocessable Entity` on schema violation.

---

## 3. `POST /api/accountability/recon-checkin`

Logs a 20-Second Recon win for a specific pillar (idempotent on `(user_email, idempotency_key)`).

```json
{
  "pillar_id": "protected-family-time",
  "iso_date": "2026-11-22",
  "minutes_spent": 90,
  "win_note": "Unplugged dinner and walk with fiancee before vacation",
  "idempotency_key": "2026-11-22-family-01",
  "source": "hub_recon"
}
```

* **Responses:** `201 Created` (or `200 OK` if deduplicated) returning the updated `PillarStreakSummary` and `graph_sync_status`.

---

## 4. `GET /api/accountability/streaks?iso_week=2026-W47`

Returns `AccountabilityDashboardResponse` with per-pillar streaks, `grace_mode_active`, `life_harmony_ratio`, and `overall_completion_ratio`.

---

## 5. `POST /api/accountability/grace-window`

Toggles Grace / Vacation Mode for an ISO week (`GraceWindowRequest`: `iso_week`, `enabled`, `reason`), freezing `grace_eligible` streaks while still rewarding restorative life wins.

---

## 6. `GET /api/accountability/export-markdown`

Returns `text/markdown` (`<= 450` lines) summarizing active pillars, weekly streaks, and recent wins—sanitized for zero-trust Git commits into `Notes_repo` or Google Drive.
