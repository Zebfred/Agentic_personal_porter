# Bolt's Journal - Critical Learnings & Operational Playbook

This document is a living record of critical learnings, architectural insights, and performance best practices accumulated during the development and maintenance of the personal porter application.

## 2026-04-18 - Safe Mocking of MongoDB Batch Operations
**Learning:** In tests mocking `bulk_write` with `unittest.mock.MagicMock`, calling `result.upserted_count` will return another mock object instead of an integer. If arithmetic operations (like `modified_count + upserted_count`) are performed on this value, it will raise `TypeError: unsupported operand type(s) for +: 'int' and 'MagicMock'`.
**Action:** When mocking `bulk_write`, explicitly set integer returns for count attributes: `mock_result.modified_count = 0` and `mock_result.upserted_count = 0`.

## 2026-03-24 - MongoDB Aggregation Pipeline Cursor Exhaustion
**Learning:** Consuming an aggregation cursor directly within a retry loop causes subsequent retry attempts to operate on an exhausted cursor, silently failing to process data on transient errors.
**Action:** Always cast aggregation cursors to a `list` before processing within retry blocks to ensure the dataset is re-iterable across retries.

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
