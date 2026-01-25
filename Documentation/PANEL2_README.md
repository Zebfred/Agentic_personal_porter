# Panel 2: LLMs - RAG System Implementation

## Overview

Panel 2 implements the "brain" of the ResearchAgent - a complete RAG (Retrieval Augmented Generation) system that enables the agent to answer questions about Reinforcement Learning using the paper database built in Panel 1.

## Components

### 1. Embeddings (`rag_core/embeddings.py`)

**SciBERTEmbedder** - Generates embeddings using SciBERT model (`allenai/scibert_scivocab_uncased`)

**Features:**
- Domain-specific embeddings optimized for scientific text
- Batch processing for efficiency
- Automatic device selection (CUDA if available, else CPU)
- 512 token limit per text (SciBERT constraint)
- 768-dimensional embeddings

**Key Methods:**
- `embed(text)` - Generate embedding for single text
- `embed_batch(texts, batch_size=32)` - Generate embeddings for batch
- `embed_chunks(chunks)` - Generate embeddings for chunk dictionaries
- `get_embedding_dim()` - Returns 768 (embedding dimension)

### 2. Vector Store (`rag_core/vector_store.py`)

**VectorStore** - Manages ChromaDB vector database

**Features:**
- Persistent storage in `data/chroma_db/`
- Cosine similarity search
- Metadata filtering support
- Automatic collection management

**Key Methods:**
- `add_chunks(chunks, embeddings)` - Add chunks with embeddings to store
- `search(query_embedding, top_k=5, filter_dict=None)` - Search for similar chunks
- `get_collection_size()` - Get number of chunks in collection
- `clear_collection()` - Clear all chunks

### 3. Query Engine (`rag_core/query_engine.py`)

**RAGQueryEngine** - Orchestrates RAG query processing

**Features:**
- Retrieves relevant chunks using vector similarity
- Constructs prompts with retrieved context
- Uses Groq LLM (llama-3.3-70b-versatile) for answer generation
- Returns answers with source citations
- Low temperature (0.1) for factual answers

**Key Methods:**
- `answer_question(query, top_k=5)` - Answer question using RAG
  - Returns: `{'answer': str, 'sources': List[Dict], 'retrieved_chunks': List[Dict]}`

**Workflow:**
1. Generate query embedding using SciBERT
2. Search vector store for top-k similar chunks
3. Build context string from retrieved chunks
4. Construct prompt with query and context
5. Call LLM to generate answer
6. Extract and format source citations

## Usage

### Building the RAG Index

First, ensure you have chunks from Panel 1:
```bash
# Chunks should be in data/chunks_*.json
ls data/chunks_*.json
```

Build the index:
```bash
# Using fixed-size chunks (default)
python build_rag_index.py

# Using semantic chunks
python build_rag_index.py --chunking-strategy fast_semantic
python build_rag_index.py --chunking-strategy science_semantic

# Custom collection name
python build_rag_index.py --collection-name my_rl_papers
```

### Querying the RAG System

**Option 1: Using the query engine directly**
```python
from rag_core.query_engine import RAGQueryEngine

engine = RAGQueryEngine()
result = engine.answer_question("What is Q-learning?", top_k=5)

print(result['answer'])
for source in result['sources']:
    print(f"- {source['paper_title']}: {source['section']}")
```

**Option 2: Using the manual test script**
```bash
# Set GROQ_API_KEY in environment or .env file
export GROQ_API_KEY='your-key-here'

python test_rag_manual.py
```

**Option 3: Using the test scripts**
```bash
# Unit tests
pytest tests/test_embeddings.py -v
pytest tests/test_vector_store.py -v
pytest tests/test_query_engine.py -v

# Integration test
pytest tests/test_rag_pipeline.py -v
```

## Configuration

### Environment Variables

Required:
- `GROQ_API_KEY` - Groq API key for LLM access

Optional:
- `CUDA_VISIBLE_DEVICES` - Control GPU usage for embeddings

### Model Configuration

**Embedding Model:**
- Model: `allenai/scibert_scivocab_uncased`
- Dimension: 768
- Max tokens: 512 per text
- Device: Auto (CUDA if available)

**LLM Model:**
- Provider: Groq
- Model: `groq/llama-3.3-70b-versatile`
- Temperature: 0.1 (for factual answers)
- Configurable in `RAGQueryEngine.__init__()`

### Vector Store Configuration

- **Storage**: `data/chroma_db/` (persistent)
- **Similarity Metric**: Cosine similarity
- **Collection Name**: `rl_papers` (default, configurable)

## Architecture

```
User Query
    ↓
SciBERT Embedder → Query Embedding
    ↓
Vector Store → Retrieve Top-K Similar Chunks
    ↓
Build Context String
    ↓
Construct Prompt (Query + Context)
    ↓
Groq LLM → Generate Answer
    ↓
Format Response (Answer + Sources)
```

## Data Flow

1. **Index Building** (one-time):
   - Load chunks from JSON files
   - Generate embeddings for all chunks
   - Store in ChromaDB with metadata

2. **Query Processing** (per query):
   - Embed query text
   - Search vector store
   - Retrieve top-k chunks
   - Generate answer with LLM
   - Return answer with citations

## Dependencies

Core dependencies (already in `requirements.txt`):
- `transformers>=4.30.0` - For SciBERT model
- `torch>=2.0.0` - PyTorch for model inference
- `chromadb==0.5.23` - Vector database
- `langchain-groq==0.3.7` - Groq LLM integration
- `python-dotenv==1.1.1` - Environment variable management

## Testing

### Unit Tests
- `tests/test_embeddings.py` - Embedding generation tests
- `tests/test_vector_store.py` - Vector store operations tests
- `tests/test_query_engine.py` - Query engine logic tests

### Integration Tests
- `tests/test_rag_pipeline.py` - End-to-end pipeline test

### Manual Testing
- `test_rag_manual.py` - Interactive testing with real queries

## Performance Considerations

### Embedding Generation
- **Batch Size**: Default 32 (configurable)
- **Device**: Auto-selects CUDA if available
- **Speed**: ~500-1000ms per batch on CPU, ~100-200ms on GPU

### Vector Search
- **Index Type**: HNSW (Hierarchical Navigable Small World)
- **Similarity**: Cosine similarity
- **Search Speed**: <10ms for typical queries

### LLM Generation
- **Provider**: Groq (fast inference)
- **Model**: llama-3.3-70b-versatile
- **Response Time**: ~1-3 seconds per query

## Known Limitations

1. **SciBERT Token Limit**: 512 tokens per text
   - Long chunks are truncated
   - Consider using FastSemanticChunking for longer texts

2. **Single Collection**: Currently supports one collection at a time
   - Can create multiple VectorStore instances for different collections

3. **No Reranking**: Uses simple top-k retrieval
   - Could add cross-encoder reranking for better results

4. **No Query Expansion**: Direct query embedding only
   - Could add query expansion/rewriting for better retrieval

## Future Enhancements

1. **Hybrid Search**: Combine semantic and keyword search
2. **Reranking**: Add cross-encoder reranking for better precision
3. **Query Expansion**: Expand queries with related terms
4. **Multi-Collection Support**: Support multiple paper collections
5. **Caching**: Cache embeddings and query results
6. **Evaluation Metrics**: Add RAG quality evaluation (BLEU, ROUGE, etc.)

## Next Steps (Panel 3)

Panel 3 will integrate this RAG system into the main application:
- FastAPI service wrapper
- Docker containerization
- Integration with CrewAI agents
- Production deployment

