# Structured Logging Implementation

## Overview

Added comprehensive structured logging to the FastAPI RAG service to improve debugging, monitoring, and production observability.

## What Was Added

### 1. Logging Configuration
- Configured Python's `logging` module with structured format
- Timestamp, logger name, level, and message format
- Easy to extend to JSON logging for production

### 2. Request/Response Logging Middleware
- Logs all HTTP requests with:
  - Method and path
  - Client IP
  - Query parameters
  - Response status code
  - Processing time
- Adds `X-Process-Time` header to responses

### 3. Application Lifecycle Logging
- **Startup**: Logs service initialization, environment, configuration checks
- **Shutdown**: Logs graceful shutdown
- Checks for required environment variables (GROQ_API_KEY)
- Verifies vector store availability

### 4. Endpoint-Specific Logging

#### Root Endpoint (`/`)
- Debug-level logging for basic access

#### Health Endpoint (`/health`)
- Logs health check requests
- Logs vector store size
- Error logging with full stack traces

#### Query Endpoint (`/query`)
- **Request logging**: Query text (truncated), top_k parameter
- **Processing logging**: Query engine initialization, vector store size
- **Success logging**: Processing time, retrieved chunks count, sources count, answer length
- **Error logging**: Full error details with stack traces

#### Rebuild Index Endpoint (`/rebuild_index`)
- **Request logging**: Strategy, collection name
- **Processing logging**: Chunk loading, index building progress
- **Success logging**: Total time, chunks indexed, final collection size
- **Error logging**: Full error details with stack traces

## Log Levels Used

- **INFO**: Normal operations, successful requests, important state changes
- **DEBUG**: Detailed information for debugging
- **WARNING**: Non-critical issues (missing config, empty vector store)
- **ERROR**: Failures with full stack traces

## Example Log Output

```
2025-11-13 10:30:15 - __main__ - INFO - Starting ResearchAgent RAG Service
2025-11-13 10:30:15 - __main__ - INFO - Service version: 1.0.0
2025-11-13 10:30:15 - __main__ - INFO - GROQ_API_KEY configured
2025-11-13 10:30:15 - __main__ - INFO - Vector store initialized with 256 chunks
2025-11-13 10:30:20 - __main__ - INFO - Request: GET /health
2025-11-13 10:30:20 - __main__ - INFO - Health check: healthy, vector_store_size=256
2025-11-13 10:30:20 - __main__ - INFO - Response: GET /health - 200
2025-11-13 10:30:25 - __main__ - INFO - Request: POST /query
2025-11-13 10:30:25 - __main__ - INFO - Processing query: 'What is Q-learning?' (top_k=5)
2025-11-13 10:30:26 - __main__ - INFO - Query completed successfully in 1.23s
2025-11-13 10:30:26 - __main__ - INFO - Response: POST /query - 200
```

## Benefits

1. **Debugging**: Easy to trace issues with detailed request/response logs
2. **Performance Monitoring**: Processing times logged for all operations
3. **Production Ready**: Structured format easy to parse and analyze
4. **Error Tracking**: Full stack traces for all errors
5. **Audit Trail**: Complete record of all API operations
6. **Observability**: Clear visibility into service behavior

## Future Enhancements

1. **JSON Logging**: Switch to JSON format for log aggregation tools
2. **Log Rotation**: Configure log rotation for production
3. **External Logging**: Send logs to external services (e.g., ELK, CloudWatch)
4. **Metrics**: Add metrics endpoint for Prometheus
5. **Request IDs**: Add unique request IDs for tracing
6. **User Context**: Add user/session information when available

## Usage

The logging is automatic - no code changes needed in calling code. All endpoints now log:

- Request details
- Processing steps
- Success/failure status
- Timing information
- Error details (when errors occur)

## Configuration

Log level can be controlled via environment variable:

```bash
export LOG_LEVEL=DEBUG  # For detailed debugging
export LOG_LEVEL=INFO   # For normal operation (default)
export LOG_LEVEL=WARNING  # For production (minimal logging)
```

## Testing

All existing tests continue to pass. The logging is non-intrusive and doesn't affect functionality.

## Files Modified

- `rag_service.py`: Added logging configuration, middleware, and endpoint logging
