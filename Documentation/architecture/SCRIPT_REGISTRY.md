# Project Script Registry

This document formally maps the execution environment of the Agentic Personal Porter's `src/` directory. For each sub-module, it lists the active scripts, their internal dependencies (how they rely on the rest of the project `src.*`), and their core functional definitions. 

---

## 1. `src/agents/`
Responsible for the intelligence layer and crew execution.

### `crew_manager_mach2.py`
- **Imports:** `src.utils.path_utils.load_env_vars, get_auth_file`, `src.database.context_engine.SovereignContextEngine`
- **Functions:**
  - `get_mach2_context()`
  - `run_crew(journal_entry: str, log_data: dict = None)`

### `gtky_brain.py`
- **Imports:** `src.utils.path_utils.load_env_vars, get_auth_file`, `src.database.neo4j_client.get_driver`

### `gtky_librarian.py`
- **Imports:** `src.utils.path_utils.load_env_vars, get_project_root`, `src.database.neo4j_client.get_driver`

### `Socratic_mirror_logic.py`
- **Imports:** `src.database.context_engine.SovereignContextEngine`, `src.database.mongo_storage.SovereignMongoStorage`


---

## 2. `src/integrations/`
Responsible for third-party API ingestion and parsing.

### `google_calendar_authentication_helper.py`
- **Functions:**
  - `get_auth_paths()`
  - `get_calendar_credentials(scopes=None)`

### `google_calendar.py`
- **Imports:** `src.integrations.google_calendar_authentication_helper.get_calendar_credentials`
- **Functions:**
  - `get_calendar_service()`

### `calendar_parser.py`
- **Imports:** `src.constants.ACTUAL_CATEGORY_MAPPING`
- **Functions:**
  - `get_time_chunk(hour)`
  - `determine_category(title, color_id)`
  - `parse_single_event(event)`
  - `event_record_type(event)`
  - `parse_calendar_to_intentions(raw_events)`
  - `save_debug_artifacts(raw_data, formatted_data)`

---

## 3. `src/database/` & Submodules
Responsible for state persistence across Mongo and Neo4j.

### `mongo_storage.py`
- **Imports:** `src.config.MongoConfig`, `src.integrations.calendar_parser.parse_single_event`

### `context_engine.py`
- **Imports:** `src.config.NeoConfig`
- **Functions:**
  - `run_15min_sanity_test()`

### `inject_hero_calendar.py`
- **Imports:** `src.config.NeoConfig`, `src.constants.ACTUAL_CATEGORY_MAPPING`

### `inject_hero_foundation.py`
- **Imports:** `src.config.NeoConfig`
- **Functions:**
  - `flatten_intents(raw_intents)`
  - `process_epochs(raw_epochs)`
  - `inject_hero_data(hero_name=None)`

### `neo4j_client/connection.py`
- **Imports:** `src.config.NeoConfig`
- **Functions:**
  - `get_driver()`

### `neo4j_client/read_operations.py`
- **Functions:**
  - `get_valuable_detours(user_name=None)`
  - `get_user_patterns(user_id: str)`
  - `_get_patterns_tx(tx, user_id: str)`
  - `get_goal_progress(user_id: str, goal_id: str = None)`
  - `_get_specific_goal_progress_tx(tx, user_id: str, goal_id: str)`
  - `_get_all_goals_progress_tx(tx, user_id: str)`
  - `get_state_correlations(user_id: str)`
  - `_get_state_correlations_tx(tx, user_id: str)`

### `neo4j_client/write_operations.py`
- **Functions:**
  - `log_to_neo4j(log_data: dict)`
  - `_create_log_entry(tx, log_data: dict)`
  - `create_identity_graph(user_id, origin_story, ambitions)`
  - `create_goal(...)`
  - `_create_goal_tx(...)`
  - `_extract_time_of_day(time_chunk_id: str)`

---

## 4. `src/orchestrators/`
Responsible for multi-step data pipelines.

### `sync_calendar_to_graph.py`
- **Imports:** `src.database.mongo_storage.SovereignMongoStorage`, `src.database.inject_hero_calendar.SovereignGraphInjector`, `src.integrations.calendar_parser.parse_calendar_to_intentions`
- **Functions:**
  - `run_sync_pipeline(hero_name=None)`

---

## 5. `src/utils/` & Core App
Utility layer and main API endpoints.

### `utils/path_utils.py`
- **Functions:**
  - `get_project_root()`
  - `load_env_vars()`
  - `get_auth_file(filename: str)`

### `app.py`
- **Imports:** `src.agents.crew_manager_mach2.run_crew`, `src.database.neo4j_client.log_to_neo4j`, `src.database.mongo_storage.SovereignMongoStorage`, `src.integrations.google_calendar.get_calendar_service`, `src.schemas.api_models.JournalRequestSchema`, `src.schemas.api_models.CalendarRequestSchema`
- **Functions:**
  - `require_api_key(f)`
  - `index()`
  - `inventory()`
  - `artifacts()`
  - `serve_js(filename)`
  - `get_calendar_service_instance()`
  - `fetch_calendar_events_for_date(target_date_str: str)`
  - `process_journal()`
  - `get_inventory()`
  - `manage_artifact(artifact_name)`
  - `get_calendar_events()`
  - `admin_sync_calendar()`
  - `admin_inject_foundation()`
