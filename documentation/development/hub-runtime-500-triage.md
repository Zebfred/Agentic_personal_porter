# Runtime 500 Triage: Local MongoDB & `mongomock` Transition (`logs/app.log`)

**Date:** 2026-10-25  
**Scope:** Runtime log inspection of `uv run python src/app.py` (`127.0.0.1:5090`) while browsing `frontend/index.html` after the `003-first-serving-hub-api` implementation and the zero-cost local MongoDB (`MONGO_URI=mongodb://localhost:27017/personal_porter`) transition.

---

## 1. Executive Summary

When running `uv run python src/app.py` directly on the host without a running local MongoDB daemon (`mongod` or `docker compose up -d mongo` on port `27017`), **`frontend/index.html` triggers a cascade of HTTP 500 Internal Server Errors** across 7 concurrent dashboard startup calls, each hanging for **30 seconds** before failing with:

```text
pymongo.errors.ServerSelectionTimeoutError: localhost:27017: [Errno 111] Connection refused
(configured timeouts: socketTimeoutMS: 20000.0ms, connectTimeoutMS: 20000.0ms), Timeout: 30s
```

By contrast, running `pytest` succeeds offline because `tests/conftest.py` patches `pymongo.MongoClient` with `mongomock.MongoClient`. The live Flask server (`src/app.py`) does not currently activate `mongomock` or fail-fast timeouts when `localhost:27017` is unreachable.

---

## 2. Catalog of Runtime Errors Observed in `logs/app.log`

| Timestamp (`logs/app.log`) | Endpoint / Caller | Log Message & Exception | Status |
| :--- | :--- | :--- | :--- |
| `20:24:34,294` | `GET /api/artifacts/scan` (`src/routes/inventory_routes.py:88`) | `ValidationError: 1 validation error for ArtifactGapItem — artifact_name Field required` | **FIXED** in `src/agents/gtky_identity_architect.py` & `src/schemas/hub_models.py` |
| `20:40:01,693` & `20:40:15,865` | `POST /api/login` (`src/routes/user_routes.py`) | `Failed to sync user <email> to MongoDB: localhost:27017: [Errno 111] Connection refused (Timeout: 30s)` | **Non-fatal warning** (caught in `/api/login`, JWT still issued after 30s delay) |
| `20:40:32,238` | `GET /api/chat/welcome` (`src/routes/chat_routes.py:66`) | `Error in First-Serving Porter welcome` -> `SovereignMongoStorage().__init__()` -> `_ensure_indexes()` -> `ServerSelectionTimeoutError` | **Fixable 500** |
| `20:40:32,296` | `GET /api/artifacts/scan` (`src/routes/inventory_routes.py:83`) | `Error scanning artifacts` -> `SovereignMongoStorage().__init__()` -> `_ensure_indexes()` -> `ServerSelectionTimeoutError` | **Fixable 500** |
| `20:40:32,397` | `GET /api/journal/history` (`src/routes/journal_routes.py:502`) | `Error fetching journal history` -> `SovereignMongoStorage().__init__()` -> `_ensure_indexes()` -> `ServerSelectionTimeoutError` | **Fixable 500** |
| `20:40:32,482` | `GET /api/user/hub_metrics` (`src/routes/user_routes.py:166`) | `Error computing hub metrics` -> `SovereignMongoStorage().__init__()` -> `_ensure_indexes()` -> `ServerSelectionTimeoutError` | **Fixable 500** |
| `20:40:33,567` | `GET /api/calendar/unverified_audits` (`src/routes/calendar_routes.py:178`) | `Error fetching unverified audits` -> `AuditInspector.batch_unverified_records()` -> `AgentHealthManager.start_agent_run()` -> `ServerSelectionTimeoutError` | **Fixable 500** |
| `20:41:02,564` | `GET /api/calendar/adventure_log` (`src/routes/calendar_routes.py`) | `Error getting adventure log delta` -> `SovereignMongoStorage().__init__()` -> `ServerSelectionTimeoutError` | **Fixable 500** |
| `20:41:03,629` | `GET /api/calendar/verified_history` (`src/routes/calendar_routes.py:199`) | `Error fetching verified history` -> `AuditInspector.get_recently_verified_records()` -> `self.daily_col.find()` -> `ServerSelectionTimeoutError` | **Fixable 500** |

---

## 3. Root Causes & Architectural Diagnosis

### RC-1: Split Client Instantiation (`SovereignMongoStorage` vs. `MongoConnectionManager`)
- `src/database/mongo_client/connection.py` defines `MongoConnectionManager.get_client()`, a singleton `MongoClient`.
- However, `SovereignMongoStorage.__init__()` (`src/database/mongo_storage.py:27`) bypasses `MongoConnectionManager` and creates a brand-new `MongoClient(MongoConfig.MONGO_URI)` on every instantiation.
- **Fix:** Route `SovereignMongoStorage.__init__()` through `MongoConnectionManager.get_client()` so connection pooling, timeouts, and mock fallbacks are controlled in one singleton place.

### RC-2: 30-Second Default `serverSelectionTimeoutMS` Blocking Flask Threads
- `MongoClient(MongoConfig.MONGO_URI)` uses PyMongo's default `serverSelectionTimeoutMS=30000` (30 seconds).
- When `index.html` loads and fires 7 parallel `fetch()` requests while `localhost:27017` is down, each request blocks for 30 seconds before returning HTTP 500.
- **Fix:** Configure `serverSelectionTimeoutMS=3000` (3 seconds) and `connectTimeoutMS=3000` for local/dev connections in `MongoConnectionManager`.

### RC-3: Unprotected `create_index` Calls in `SovereignMongoStorage._ensure_indexes()`
- In `src/database/mongo_storage.py:51-54`, `self.raw_col.create_index(...)` and `self.formatted_col.create_index(...)` execute **outside** the `try...except Exception` block on lines 57–69.
- Because `self.raw_col.create_index(...)` raises `ServerSelectionTimeoutError` on line 51:
  1. `SovereignMongoStorage()` crashes inside `__init__()` before any route handler can use local JSON/file fallbacks (such as `scan_artifacts` reading `data/hero_artifacts/hero_origin.json` or `chat_welcome` generating an offline greeting).
  2. `self.__class__._indexes_ensured = True` (line 71) is never reached, so every subsequent HTTP request repeats the full index-creation network round-trip.
- **Fix:** Wrap the entire `_ensure_indexes()` body in `try...except Exception as e:` and set `self.__class__._indexes_ensured = True` (or a cooldown timestamp) so offline local runs do not repeatedly block on index creation.

### RC-4: No Automatic `mongomock` Fallback When `localhost:27017` Is Offline in Dev Mode
- During `pytest`, `mongomock.MongoClient` is injected by `tests/conftest.py`.
- During interactive GUI testing via `uv run python src/app.py`, if the developer has not started Docker (`docker compose up -d mongo`), `localhost:27017` refuses connections.
- **Fix:** Enhance `MongoConnectionManager.get_client()` in `src/database/mongo_client/connection.py` so that:
  1. If `MONGO_USE_MOCK=true` is set in `.auth/.env` or environment, it directly returns a singleton `mongomock.MongoClient()`.
  2. In non-production local mode (`mongodb://localhost:27017...`), it performs a fast probe (`serverSelectionTimeoutMS=1500`); if `localhost:27017` refuses connection and `mongomock` is installed, it logs a clear warning (`WARNING: Local MongoDB on localhost:27017 unreachable; falling back to in-memory mongomock for local GUI session`) and falls back to `mongomock.MongoClient()`.

### RC-5: `AuditInspector` Hard Crash on `AgentHealthManager.start_agent_run()`
- In `src/agents/audit_inspector.py:30`, `batch_unverified_records()` calls `health_manager.start_agent_run(...)`, which performs an unguarded `self.collection.insert_one(payload)` before querying records.
- **Fix:** Make `AgentHealthManager.start_agent_run()` and `complete_agent_run()` non-fatal (log a warning and return `None` if MongoDB is unavailable) so telemetry failures never crash user-facing routes.

---

## 4. Prioritized Remediation Checklist

- [ ] **Fix 1 (`src/database/mongo_client/connection.py`)**: Add fast `serverSelectionTimeoutMS` (`2500ms`) and automatic `mongomock.MongoClient` dev fallback when `localhost:27017` is unreachable or `MONGO_USE_MOCK=true`.
- [ ] **Fix 2 (`src/database/mongo_storage.py`)**: Refactor `SovereignMongoStorage.__init__()` to reuse `MongoConnectionManager.get_client()` and wrap all `create_index` calls inside `_ensure_indexes()` within `try...except Exception` so `__init__()` never raises on index creation.
- [ ] **Fix 3 (`src/database/mongo_client/agent_health.py`)**: Guard `start_agent_run` and `complete_agent_run` with `try...except Exception` so telemetry writes cannot cause HTTP 500s on `/api/calendar/unverified_audits`.
- [ ] **Fix 4 (`src/routes/chat_routes.py` & `src/routes/inventory_routes.py`)**: Guard `SovereignMongoStorage().get_user_by_email()` in `/api/chat/welcome` and `/api/artifacts/scan` so filesystem-backed artifact scans (`data/hero_artifacts/`) and welcome messages succeed even if MongoDB is empty or degraded.
