# Bolt's Journal - Critical Learnings & Operational Playbook

This document is a living record of critical learnings, architectural insights, and performance best practices accumulated during the development and maintenance of the personal porter application.

## 2026-04-18 - Safe Mocking of MongoDB Batch Operations
**Learning:** In tests mocking `bulk_write` with `unittest.mock.MagicMock`, calling `result.upserted_count` will return another mock object instead of an integer. If arithmetic operations (like `modified_count + upserted_count`) are performed on this value, it will raise `TypeError: unsupported operand type(s) for +: 'int' and 'MagicMock'`.
**Action:** When mocking `bulk_write`, explicitly set integer returns for count attributes: `mock_result.modified_count = 0` and `mock_result.upserted_count = 0`.

## 2026-03-24 - MongoDB Aggregation Pipeline Cursor Exhaustion
**Learning:** Consuming an aggregation cursor directly within a retry loop causes subsequent retry attempts to operate on an exhausted cursor, silently failing to process data on transient errors.
**Action:** Always cast aggregation cursors to a `list` before processing within retry blocks to ensure the dataset is re-iterable across retries.

## 2024-04-16 - Neo4j Connection Pooling Performance Bottleneck
**Learning:** Creating a new `GraphDatabase.driver` instance per function call defeats the built-in connection pooling mechanisms, causing a massive performance overhead in environments running multiple fast, concurrent queries.
**Action:** Always wrap `GraphDatabase.driver` instances in a singleton pattern (or inject a shared instance) so the Neo4j Python driver can maintain and reuse its internal pool of connections. Remove manual `driver.close()` calls when using a singleton, and rely on `driver.session()` contexts to manage query lifecycles.

## 2025-02-23 - Flask Teardown Destroying Connection Pools
**Learning:** In Flask applications, `@app.teardown_appcontext` is executed at the end of every individual HTTP request. Binding `close_driver()` to this hook destroys the database connection pool after every request, negating any performance benefits of a global singleton and forcing expensive reconnections.
**Action:** Never tie long-lived connection pool closures (like Neo4j drivers) to per-request teardown hooks in Flask. Let the driver singleton manage its own connection lifecycle globally across requests.

## 2024-11-20 - [Performance Bottleneck Fixed]
**Learning:** Found an N+1 query vulnerability when iterating and calling `update_one` on the database connection in a loop.
**Action:** Replaced sequential updates with bulk updates via `UpdateOne` and `bulk_write` method.

## 2026-04-30 - Optimize audit inspector database writes with MongoDB bulk_write
**Learning:** In MongoDB, iterative updates within loops using `update_one` cause multiple network roundtrips, which can become a major latency bottleneck, especially for batch operations.
**Action:** Replace multiple `update_one` calls inside loops with batched `UpdateOne` objects and execute them in a single `bulk_write(ops, ordered=False)` call outside the loop to minimize network roundtrips.

## 2026-06-11 - Bulk Database Writes
**Learning:** When using `ruff` to verify linting or formatting, never use the `--fix` flag on the entire `src/` directory (e.g., `uv run ruff check src --fix`), as it introduces widespread, out-of-scope architectural or formatting changes that violate strict operation boundaries.
**Action:** Run linting without `--fix` or apply fixes only to explicitly modified files.

## 2025-02-23 - Batch Updates in Timeseries Collection (Event Processor)
**Learning:** When replacing sequential `update_one`/`update_many` calls inside a loop with bulk operations, it is easy to accidentally drop updates for auxiliary collections (like `timeseries_col` closing the loop) if they aren't explicitly migrated to a corresponding ops array.
**Action:** Ensure all sequential operations from the original single-event routing method are mapped exactly to their batch counterpart `bulk_write` operations, otherwise backend integrity breaks.

## 2026-08-25 - MongoDB Field Projection
**Learning:** Returning large, unprojected fields from MongoDB (especially during batch operations) creates a hidden memory bottleneck and deserialization overhead in Python applications. Even if the database load stays similar, pulling unnecessary fields bloated memory usage by up to 97% on large data batches.
**Action:** Always apply projection dicts when querying MongoDB for batch operations or operations pulling down many documents, unless every field is strictly required. This is particularly important for functions retrieving hundreds of items for transformations or filtering.

## 2026-06-25 - Query Projection for Document Deserialization
**Learning:** When querying MongoDB for batch operations in Python, omitting a projection dictionary means fetching and deserializing the entire document (including `_id` ObjectIds and deeply nested fields). This creates significant memory bloat and deserialization overhead when only a few fields (like `gcal_id` or `sync_status`) are actually needed for subsequent processing.
**Action:** Always apply explicit projection dictionaries (e.g., `{"_id": 0, "gcal_id": 1}`) to batch `find()` queries to significantly reduce memory footprint and latency, unless every field is strictly required. However, be cautious to ensure downstream code is refactored to accommodate the missing fields.

## 2026-06-12 - Index Creation Hardcoded Collection Names
**Learning:** Index definitions should be tied to configuration variables (`MongoConfig`) instead of hardcoded strings to avoid missing indexes on new collection names after schema changes, preventing full collection scans. Also, temporal queries should use `DESCENDING` indexes for optimal performance.
**Action:** Always use constants from the config classes (e.g., `MongoConfig.INTENT_COLLECTION`) when creating database indexes, and map time-based sorting to `DESCENDING` (-1).
