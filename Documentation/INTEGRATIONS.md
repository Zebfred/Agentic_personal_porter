# System Integrations Architecture

## Philosophy: Sovereign Local Data

The core tenet of the Agentic Personal Porter is that **the system must remain fully functional, queryable, and autonomous even if external data sources are disconnected.** External services are treated as "spokes" that synchronize with the local "hub" (MongoDB, Vector DB, Neo4j), rather than acting as the source of truth.

This ensures:
1. High-speed local access for the UI and AI context.
2. Resilience against API rate limits or offline states.
3. Total ownership over aggregated insights and reflections.

---

## 1. Google Calendar Integration

### Current State
Currently, the `/api/calendar/user_sync` endpoint acts as a one-way pipeline. It pulls Google Calendar events, standardizes them, and caches them into the local MongoDB (`formatted_col`, `raw_col`) and subsequently pushes them into the Neo4j Identity Graph.

### Target Bi-Directional Architecture
To achieve true sovereignty while maintaining external convenience, the calendar integration must support seamless bi-directional syncing mapped through our existing endpoints.

#### How It Works
1. **Local Writes (The Primary Source of Truth)**
   - When a user modifies an event or chunk via the Hub or Adventure Calendar (using `/api/save_log` or the upcoming `/api/journal/edit_event`), the change is immediately committed to local MongoDB.
   - A background celery/redis worker detects this state change.
2. **Upstream Sync (Eventual Consistency)**
   - The worker executes the `/api/calendar/push_to_gcal` logic to update the remote Google Calendar. 
   - If offline, the event remains queued locally in a `sync_status: "pending_upstream"` state.
3. **Downstream Pulls (CDC)**
   - Our existing `user_sync_calendar` pipeline runs periodically to fetch upstream changes made directly in the Google UI, comparing Google's `updatedAt` timestamps against our local cache.

#### Endpoint Expansion Required
- **Modify `/api/save_log`**: Ensure that any manual chunk log modification optionally triggers an asynchronous patch to Google Calendar if the time chunk is tethered to a `gcal_id`.
- **Add Conflict Resolution Strategy**: If a local event is modified while offline, and the Google Calendar event was also modified remotely, the local Neo4j graph acts as the authoritative source.

---

## 2. Google Reflection Documents (Google Docs Integration)

### Current State
Sovereign Daily Reports and weekly expectations are currently saved natively to MongoDB (`agent_reflections` collection) and viewed exclusively within the `Adventure Time Log` and `Adventure Calendar` UI.

### Target Extracellular Backup Architecture
Many users prefer the readability, sharing, and long-term archival capabilities of Google Docs. We want to treat Google Docs as an extracellular, read-only backup of our AI-generated reflections.

#### How It Works
1. **Report Generation (Local Priority)**
   - The First-Serving Porter generates a Sovereign Daily Report.
   - It is immediately committed to MongoDB and embedded into the local Vector DB (Weaviate).
2. **Google Drive Export Pipeline**
   - We will introduce a new background worker: `orchestrators.export_reflection_to_doc`.
   - Once the reflection is saved locally, this worker calls the Google Drive / Google Docs API to create (or append to) a running "Sovereign Journal [YYYY]" document.
3. **Lineage Tracking**
   - The resulting Google Doc URL is written back to the MongoDB reflection record.
   - The UI (e.g., the modal deep-dive) can display a small "Open in Google Docs" button using this URL.

#### Endpoint Expansion Required
- **New Endpoint**: `POST /api/journal/export_to_drive` (Can be triggered manually via the UI or automatically via background hooks).
- **Update `mongo_storage.save_agent_reflection`**: Expand schema to accept `google_doc_url` and `google_doc_id` fields.

---

## Conclusion
By positioning MongoDB and Neo4j as the authoritative layer, we ensure the UI remains fast and functional. Google Calendar becomes a bi-directional mirror for convenience, and Google Docs becomes a stylized, archival output. The core engine never strictly waits on external I/O to present insights to the user.
