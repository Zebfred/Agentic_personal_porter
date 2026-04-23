## 2024-04-16 - Neo4j Connection Pooling Performance Bottleneck
**Learning:** Creating a new `GraphDatabase.driver` instance per function call defeats the built-in connection pooling mechanisms, causing a massive performance overhead in environments running multiple fast, concurrent queries.
**Action:** Always wrap `GraphDatabase.driver` instances in a singleton pattern (or inject a shared instance) so the Neo4j Python driver can maintain and reuse its internal pool of connections. Remove manual `driver.close()` calls when using a singleton, and rely on `driver.session()` contexts to manage query lifecycles.

## 2025-02-23 - Flask Teardown Destroying Connection Pools
**Learning:** In Flask applications, `@app.teardown_appcontext` is executed at the end of every individual HTTP request. Binding `close_driver()` to this hook destroys the database connection pool after every request, negating any performance benefits of a global singleton and forcing expensive reconnections.
**Action:** Never tie long-lived connection pool closures (like Neo4j drivers) to per-request teardown hooks in Flask. Let the driver singleton manage its own connection lifecycle globally across requests.
