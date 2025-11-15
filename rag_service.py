"""
FastAPI service for RAG query engine.

This service exposes the RAG system as a REST API with endpoints for:
- Querying the RAG system
- Health checks
- Rebuilding the index
"""

import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from rag_core.query_engine import RAGQueryEngine
from rag_core.vector_store import VectorStore
from rag_core.embeddings import SciBERTEmbedder
from build_rag_index import build_index, load_chunks

load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="ResearchAgent RAG Service",
    description="RAG service for querying Reinforcement Learning research papers",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global query engine instance (lazy initialization)
_query_engine: Optional[RAGQueryEngine] = None


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
        vector_store = VectorStore()
        collection_size = vector_store.get_collection_size()
        
        return HealthResponse(
            status="healthy",
            vector_store_size=collection_size,
            service="ResearchAgent RAG Service"
        )
    except Exception as e:
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
    try:
        # Check for API key
        if not os.getenv('GROQ_API_KEY'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="GROQ_API_KEY not configured"
            )
        
        # Get query engine
        engine = get_query_engine()
        
        # Check if vector store has data
        vector_store = VectorStore()
        if vector_store.get_collection_size() == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vector store is empty. Please rebuild the index first using /rebuild_index"
            )
        
        # Process query
        result = engine.answer_question(request.query, top_k=request.top_k)
        
        return QueryResponse(
            query=request.query,
            answer=result['answer'],
            sources=result['sources'],
            retrieved_chunks_count=len(result.get('retrieved_chunks', []))
        )
        
    except HTTPException:
        raise
    except Exception as e:
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
    try:
        # Determine chunk file
        chunk_file_map = {
            'fixed': 'data/chunks_fixed.json',
            'fast_semantic': 'data/chunks_fast_semantic.json',
            'science_semantic': 'data/chunks_science_semantic.json'
        }
        
        if chunking_strategy not in chunk_file_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid chunking_strategy. Must be one of: {list(chunk_file_map.keys())}"
            )
        
        chunk_file = Path(chunk_file_map[chunking_strategy])
        
        if not chunk_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chunk file not found: {chunk_file}"
            )
        
        # Load chunks
        chunks = load_chunks(chunk_file)
        
        # Build index
        vector_store = build_index(
            chunks,
            collection_name=collection_name,
            batch_size=32
        )
        
        # Reset query engine to use new index
        global _query_engine
        _query_engine = None
        
        return RebuildIndexResponse(
            status="success",
            message=f"Index rebuilt successfully using {chunking_strategy} chunks",
            chunks_indexed=len(chunks),
            collection_name=collection_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rebuilding index: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

