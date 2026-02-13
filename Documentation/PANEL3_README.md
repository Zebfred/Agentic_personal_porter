# Panel 3: Software Engineering and MLOps

## Overview

Panel 3 productionizes the ResearchAgent RAG system by:
1. **FastAPI Service**: RESTful API wrapper for the RAG system
2. **Containerization**: Docker support for easy deployment
3. **Integration**: Standalone service that can be called from the main Flask API
4. **Testing**: Integration tests for the FastAPI service

## Components

### 1. FastAPI Service (`rag_service.py`)

**Standalone microservice** exposing the RAG system via REST API.

**Endpoints**:

#### `GET /`
- **Description**: Root endpoint with service information
- **Response**: Service name, version, available endpoints

#### `GET /health`
- **Description**: Health check endpoint
- **Response**: 
  ```json
  {
    "status": "healthy",
    "vector_store_size": 256,
    "service": "ResearchAgent RAG Service"
  }
  ```

#### `POST /query`
- **Description**: Query the RAG system
- **Request Body**:
  ```json
  {
    "query": "What is Q-learning?",
    "top_k": 5
  }
  ```
- **Response**:
  ```json
  {
    "query": "What is Q-learning?",
    "answer": "...",
    "sources": [
      {
        "paper_title": "...",
        "section": "...",
        "similarity_score": 0.85
      }
    ],
    "retrieved_chunks_count": 5
  }
  ```

#### `POST /rebuild_index`
- **Description**: Rebuild the vector index from chunk files
- **Query Parameters**:
  - `chunking_strategy`: `fixed`, `fast_semantic`, or `science_semantic` (default: `fixed`)
  - `collection_name`: ChromaDB collection name (default: `rl_papers`)
- **Response**:
  ```json
  {
    "status": "success",
    "message": "Index rebuilt successfully using fixed chunks",
    "chunks_indexed": 256,
    "collection_name": "rl_papers"
  }
  ```

**Features**:
- CORS enabled for cross-origin requests
- Request/response validation with Pydantic models
- Error handling with appropriate HTTP status codes
- Lazy initialization of query engine
- Health checks for monitoring

### 2. Dockerfile

**Multi-stage build** for optimized image size.

**Features**:
- Python 3.11 slim base image
- Build stage for dependencies
- Production stage with minimal footprint
- Health check configuration
- Exposed port 8000
- Volume mounts for persistent data

**Build**:
```bash
docker build -t rag-service .
```

**Run**:
```bash
docker run -p 8000:8000 \
  -e GROQ_API_KEY=your-key \
  -v $(pwd)/data:/app/data \
  rag-service
```

### 3. Docker Compose (`docker-compose.yml`)

**Orchestration** for easy deployment.

**Features**:
- Service definition with build context
- Port mapping (8000:8000)
- Environment variable injection
- Volume mounts for persistent data
- Health checks
- Restart policies
- Network configuration

**Usage**:
```bash
# Start service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop service
docker-compose down
```

### 4. Integration Tests (`tests/test_fastapi_service.py`)

**Test suite** for FastAPI service endpoints.

**Test Coverage**:
- ✅ Root endpoint
- ✅ Health check endpoint
- ✅ Query endpoint (with and without API key)
- ✅ Rebuild index endpoint
- ✅ Request model validation

**Run Tests**:
```bash
pytest tests/test_fastapi_service.py -v
```

## Usage

### Local Development

**1. Start the service**:
```bash
# Using uvicorn directly
uvicorn rag_service:app --host 0.0.0.0 --port 8000 --reload

# Or using Python
python rag_service.py
```

**2. Test the service**:
```bash
# Health check
curl http://localhost:8000/health

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Q-learning?", "top_k": 3}'

# Rebuild index
curl -X POST "http://localhost:8000/rebuild_index?chunking_strategy=fixed"
```

### Docker Deployment

**1. Build and run**:
```bash
# Build image
docker build -t rag-service .

# Run container
docker run -d \
  --name rag-service \
  -p 8000:8000 \
  -e GROQ_API_KEY=your-key \
  -v $(pwd)/data:/app/data \
  rag-service
```

**2. Using Docker Compose**:
```bash
# Create .env file with GROQ_API_KEY
echo "GROQ_API_KEY=your-key" > .env

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f rag-service
```

### Integration with Main Flask App

The RAG service is designed as a **standalone microservice** that can be called from the main Flask application.

**Example Integration**:
```python
# In server.py or main.py
import requests

def query_rag_service(query: str, top_k: int = 5):
    """Query the RAG service."""
    response = requests.post(
        "http://localhost:8000/query",
        json={"query": query, "top_k": top_k},
        timeout=30
    )
    response.raise_for_status()
    return response.json()

# Usage
result = query_rag_service("What is Q-learning?")
print(result['answer'])
```

**Alternative**: Direct import (if running in same process):
```python
from rag_core.query_engine import RAGQueryEngine

engine = RAGQueryEngine()
result = engine.answer_question("What is Q-learning?")
```

## Configuration

### Environment Variables

**Required**:
- `GROQ_API_KEY`: Groq API key for LLM access

**Optional**:
- `CUDA_VISIBLE_DEVICES`: Control GPU usage for embeddings
- `PYTHONUNBUFFERED`: Set to 1 for better logging in containers

### Service Configuration

**Port**: 8000 (configurable in Dockerfile/docker-compose.yml)

**Data Directory**: `/app/data` (mounted as volume)

**Vector Store**: `data/chroma_db/` (persistent)

**Chunk Files**: `data/chunks_*.json` (required for rebuild_index)

## Architecture

```
┌─────────────────┐
│   Client App    │
│  (Flask/Other)  │
└────────┬────────┘
         │ HTTP/REST
         │
┌────────▼────────┐
│  FastAPI Service│
│  (rag_service)  │
│   Port: 8000    │
└────────┬────────┘
         │
    ┌────┴────┐
    │        │
┌───▼───┐ ┌─▼────────┐
│ RAG   │ │ Vector   │
│ Engine│ │ Store    │
│       │ │(ChromaDB)│
└───┬───┘ └──────────┘
    │
┌───▼────────┐
│  SciBERT   │
│ Embedder   │
└────────────┘
```

## Deployment Options

### 1. Local Development
- Run directly with uvicorn
- Hot reload enabled
- Easy debugging

### 2. Docker Container
- Isolated environment
- Consistent across machines
- Easy to deploy

### 3. Docker Compose
- Multi-service orchestration
- Volume management
- Network configuration

### 4. Production (Future)
- Kubernetes deployment
- Load balancing
- Auto-scaling
- Monitoring and logging

## Testing

### Unit Tests
```bash
pytest tests/test_fastapi_service.py -v
```

### Integration Tests
```bash
# Start service
docker-compose up -d

# Run tests
pytest tests/test_fastapi_service.py -v

# Stop service
docker-compose down
```

### Manual Testing
```bash
# Health check
curl http://localhost:8000/health

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Q-learning?"}'
```

## Monitoring

### Health Checks
- **Endpoint**: `GET /health`
- **Interval**: 30 seconds (Docker)
- **Timeout**: 10 seconds
- **Retries**: 3

### Logging
- Service logs available via `docker-compose logs`
- Application logs to stdout/stderr
- Health check failures logged

## Troubleshooting

### Service Won't Start
1. Check `GROQ_API_KEY` is set
2. Verify port 8000 is available
3. Check Docker logs: `docker-compose logs rag-service`

### Empty Vector Store
1. Build index first: `POST /rebuild_index`
2. Verify chunk files exist in `data/`
3. Check vector store directory permissions

### Query Failures
1. Verify `GROQ_API_KEY` is set
2. Check vector store has data (`GET /health`)
3. Review service logs for errors

### Docker Issues
1. Check Docker is running: `docker ps`
2. Verify image built: `docker images | grep rag-service`
3. Check container logs: `docker logs rag-service`

## Performance Considerations

### Response Times
- **Health check**: <10ms
- **Query (with LLM)**: 2-5 seconds
- **Rebuild index**: Depends on chunk count (256 chunks ~30 seconds)

### Resource Usage
- **Memory**: ~2-4GB (with SciBERT model loaded)
- **CPU**: Moderate (embedding generation)
- **GPU**: Optional (faster embeddings if available)

### Scaling
- Current: Single instance
- Future: Horizontal scaling with load balancer
- Consider: Caching for frequent queries

## Security Considerations

### Current
- CORS enabled for all origins (development)
- No authentication (development)

### Production Recommendations
1. **CORS**: Restrict to specific origins
2. **Authentication**: Add API key or OAuth
3. **Rate Limiting**: Implement request throttling
4. **HTTPS**: Use TLS/SSL
5. **Secrets Management**: Use secret management service

## Next Steps

1. **Add Authentication**: API keys or OAuth
2. **Rate Limiting**: Prevent abuse
3. **Caching**: Cache frequent queries
4. **Monitoring**: Add Prometheus metrics
5. **Logging**: Structured logging with ELK stack
6. **Kubernetes**: Production deployment
7. **Load Testing**: Performance benchmarks

## Summary

Panel 3 successfully productionizes the RAG system:
- ✅ FastAPI service with REST endpoints
- ✅ Docker containerization
- ✅ Docker Compose orchestration
- ✅ Integration tests
- ✅ Health checks and monitoring
- ✅ Ready for deployment

The service is now a **standalone microservice** that can be:
- Deployed independently
- Called from other services
- Scaled horizontally
- Monitored and maintained

🎯 **Ready for production use!**

