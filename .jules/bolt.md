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
## 2026-06-12 - Index Creation Hardcoded Collection Names
**Learning:** Index definitions should be tied to configuration variables (`MongoConfig`) instead of hardcoded strings to avoid missing indexes on new collection names after schema changes, preventing full collection scans. Also, temporal queries should use `DESCENDING` indexes for optimal performance.
**Action:** Always use constants from the config classes (e.g., `MongoConfig.INTENT_COLLECTION`) when creating database indexes, and map time-based sorting to `DESCENDING` (-1).
