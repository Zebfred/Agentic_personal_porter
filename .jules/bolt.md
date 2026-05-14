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

## 2024-06-25 - Replace Iterative MongoDB Updates with Bulk Write
**Learning:** Iterative updates in loops (e.g. `update_one` inside a for-loop processing calendar events) are a massive performance bottleneck due to continuous network roundtrips to the database. Replacing iterative `update_one` with batched `UpdateOne` commands executed via `bulk_write` significantly reduces latency and API overhead.
**Action:** When updating or inserting multiple records in MongoDB, always use `pymongo`'s `UpdateOne` (or similar bulk operations) and accumulate them in a list. Then execute `collection.bulk_write(ops, ordered=False)` to drastically improve performance.
