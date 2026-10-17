July 5th
- address: items with UI
- address outdated style.css
  * Note: Committed style.css is stale (missing border-indigo-200, from-indigo-50, to-blue-50 added in Adventure_Time_log.html, and retaining unused invisible, lowercase). Rebuilding via 'npm run build:css' compiles these correctly.
- [x] address failing check on github(should be addressed)
pymongo.errors.ServerSelectionTimeoutError: localhost:27017: [Errno 111] Connection refused (configured timeouts: socketTimeoutMS: 20000.0ms, connectTimeoutMS: 20000.0ms), Timeout: 30s, Topology Description: <TopologyDescription id: 6a47526b9ddc463196ee825d, topology_type: Unknown, servers: [<ServerDescription ('localhost', 27017) server_type: Unknown, rtt: None, error=AutoReconnect('localhost:27017: [Errno 111] Connection refused (configured timeouts: socketTimeoutMS: 20000.0ms, connectTimeoutMS: 20000.0ms)')>]>
=========================== short test summary info ============================
FAILED tests/integration/test_first_serving_porter.py::test_porter_chat_route - assert 500 == 200
 +  where 500 = <WrapperTestResponse streamed [500 INTERNAL SERVER ERROR]>.status_code
======= 1 failed, 64 passed, 4 skipped, 23 warnings in 165.81s (0:02:45) =======
-