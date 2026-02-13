"""
FastAPI service for RAG query engine.

This service exposes the RAG system as a REST API with endpoints for:
- Querying the RAG system
- Health checks
- Rebuilding the index
"""

import os
import logging
import time
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from rag_core.query_engine import RAGQueryEngine
from rag_core.vector_store import VectorStore
from rag_core.embeddings import SciBERTEmbedder
from rag_top_level_service.build_rag_index import build_index, load_chunks

load_dotenv()

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Global query engine instance (lazy initialization)
_query_engine: Optional[RAGQueryEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting ResearchAgent RAG Service")
    logger.info(f"Service version: 1.0.0")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    
    # Check required environment variables
    if not os.getenv('GROQ_API_KEY'):
        logger.warning("GROQ_API_KEY not set - query endpoint will not work")
    else:
        logger.info("GROQ_API_KEY configured")
    
    # Check vector store
    try:
        vs = VectorStore()
        size = vs.get_collection_size()
        logger.info(f"Vector store initialized with {size} chunks")
    except Exception as e:
        logger.warning(f"Vector store check failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ResearchAgent RAG Service")


# Initialize FastAPI app
app = FastAPI(
    title="ResearchAgent RAG Service",
    description="RAG service for querying Reinforcement Learning research papers",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with timing information."""
    start_time = time.time()
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else None,
            "query_params": dict(request.query_params)
        }
    )
    
    # Process request
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} - {response.status_code}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": f"{process_time:.3f}s"
            }
        )
        
        # Add timing header
        response.headers["X-Process-Time"] = f"{process_time:.3f}"
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Error processing {request.method} {request.url.path}: {str(e)}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
                "process_time": f"{process_time:.3f}s"
            },
            exc_info=True
        )
        raise


def get_query_engine() -> RAGQueryEngine:
    """Get or create query engine instance."""
    global _query_engine
    if _query_engine is None:
        _query_engine = RAGQueryEngine()
    return _query_engine


# Request/Response Models
class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    query: str = Field(..., description="The question to answer")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    query: str
    answer: str
    sources: list
    retrieved_chunks_count: int


class HealthResponse(BaseModel):
    """Response model for health endpoint."""
    status: str
    vector_store_size: int
    service: str


class RebuildIndexResponse(BaseModel):
    """Response model for rebuild_index endpoint."""
    status: str
    message: str
    chunks_indexed: int
    collection_name: str


# Endpoints
@app.get("/")
async def root():
    """Root endpoint with service information."""
    logger.debug("Root endpoint accessed")
    return {
        "service": "ResearchAgent RAG Service",
        "version": "1.0.0",
        "endpoints": {
            "/health": "GET - Health check",
            "/query": "POST - Query the RAG system",
            "/rebuild_index": "POST - Rebuild the vector index"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    try:
        logger.debug("Health check requested")
        vector_store = VectorStore()
        collection_size = vector_store.get_collection_size()
        
        logger.info(f"Health check: healthy, vector_store_size={collection_size}")
        
        return HealthResponse(
            status="healthy",
            vector_store_size=collection_size,
            service="ResearchAgent RAG Service"
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service unhealthy: {str(e)}"
        )


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """
    Query the RAG system.
    
    Args:
        request: QueryRequest with query and top_k
        
    Returns:
        QueryResponse with answer, sources, and metadata
    """
    query_start_time = time.time()
    
    try:
        logger.info(
            f"Processing query: '{request.query[:100]}...' (top_k={request.top_k})",
            extra={"query_length": len(request.query), "top_k": request.top_k}
        )
        
        # Check for API key
        if not os.getenv('GROQ_API_KEY'):
            logger.error("Query failed: GROQ_API_KEY not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GROQ_API_KEY not configured"
            )
        
        # Get query engine
        engine = get_query_engine()
        logger.debug("Query engine initialized")
        
        # Check if vector store has data
        vector_store = VectorStore()
        collection_size = vector_store.get_collection_size()
        if collection_size == 0:
            logger.warning("Query failed: Vector store is empty")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vector store is empty. Please rebuild the index first using /rebuild_index"
            )
        
        logger.debug(f"Vector store has {collection_size} chunks")
        
        # Process query
        result = engine.answer_question(request.query, top_k=request.top_k)
        
        query_time = time.time() - query_start_time
        retrieved_count = len(result.get('retrieved_chunks', []))
        sources_count = len(result.get('sources', []))
        
        logger.info(
            f"Query completed successfully in {query_time:.2f}s",
            extra={
                "query_time": f"{query_time:.2f}s",
                "retrieved_chunks": retrieved_count,
                "sources": sources_count,
                "answer_length": len(result.get('answer', ''))
            }
        )
        
        return QueryResponse(
            query=request.query,
            answer=result['answer'],
            sources=result['sources'],
            retrieved_chunks_count=retrieved_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        query_time = time.time() - query_start_time
        logger.error(
            f"Query failed after {query_time:.2f}s: {str(e)}",
            extra={"query": request.query[:100], "error": str(e)},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing query: {str(e)}"
        )


@app.post("/rebuild_index", response_model=RebuildIndexResponse)
async def rebuild_index(
    chunking_strategy: str = "fixed",
    collection_name: str = "rl_papers"
):
    """
    Rebuild the vector index from chunk files.
    
    Args:
        chunking_strategy: Chunking strategy to use (fixed, fast_semantic, science_semantic)
        collection_name: Name for the ChromaDB collection
        
    Returns:
        RebuildIndexResponse with status and metadata
    """
    rebuild_start_time = time.time()
    
    try:
        logger.info(
            f"Rebuilding index: strategy={chunking_strategy}, collection={collection_name}",
            extra={"chunking_strategy": chunking_strategy, "collection_name": collection_name}
        )
        
        # Determine chunk file
        chunk_file_map = {
            'fixed': 'data/chunks_fixed.json',
            'fast_semantic': 'data/chunks_fast_semantic.json',
            'science_semantic': 'data/chunks_science_semantic.json'
        }
        
        if chunking_strategy not in chunk_file_map:
            logger.error(f"Invalid chunking_strategy: {chunking_strategy}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid chunking_strategy. Must be one of: {list(chunk_file_map.keys())}"
            )
        
        chunk_file = Path(chunk_file_map[chunking_strategy])
        
        if not chunk_file.exists():
            logger.error(f"Chunk file not found: {chunk_file}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chunk file not found: {chunk_file}"
            )
        
        logger.info(f"Loading chunks from {chunk_file}")
        # Load chunks
        chunks = load_chunks(chunk_file)
        logger.info(f"Loaded {len(chunks)} chunks")
        
        # Build index
        logger.info("Building vector index...")
        vector_store = build_index(
            chunks,
            collection_name=collection_name,
            batch_size=32
        )
        
        final_size = vector_store.get_collection_size()
        
        # Reset query engine to use new index
        global _query_engine
        _query_engine = None
        logger.info("Query engine reset to use new index")
        
        rebuild_time = time.time() - rebuild_start_time
        
        logger.info(
            f"Index rebuilt successfully in {rebuild_time:.2f}s",
            extra={
                "chunking_strategy": chunking_strategy,
                "collection_name": collection_name,
                "chunks_indexed": len(chunks),
                "final_size": final_size,
                "rebuild_time": f"{rebuild_time:.2f}s"
            }
        )
        
        return RebuildIndexResponse(
            status="success",
            message=f"Index rebuilt successfully using {chunking_strategy} chunks",
            chunks_indexed=len(chunks),
            collection_name=collection_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        rebuild_time = time.time() - rebuild_start_time
        logger.error(
            f"Index rebuild failed after {rebuild_time:.2f}s: {str(e)}",
            extra={
                "chunking_strategy": chunking_strategy,
                "collection_name": collection_name,
                "error": str(e)
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rebuilding index: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

