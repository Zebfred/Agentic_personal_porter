"""
Unit tests for vector store.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import numpy as np
from rag_core.vector_store import VectorStore
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_vector_store():
    """Create a temporary vector store for testing."""
    temp_dir = tempfile.mkdtemp()
    store = VectorStore(
        collection_name="test_collection",
        persist_directory=temp_dir
    )
    yield store
    # Cleanup
    shutil.rmtree(temp_dir)


def test_vector_store_initialization(temp_vector_store):
    """Test VectorStore initialization."""
    assert temp_vector_store.collection is not None
    assert temp_vector_store.get_collection_size() == 0


def test_add_chunks(temp_vector_store):
    """Test adding chunks to vector store."""
    chunks = [
        {
            'text': 'First chunk about reinforcement learning.',
            'embedding': np.random.rand(768).tolist(),
            'paper_title': 'Test Paper 1',
            'chunk_index': 0
        },
        {
            'text': 'Second chunk about deep learning.',
            'embedding': np.random.rand(768).tolist(),
            'paper_title': 'Test Paper 2',
            'chunk_index': 1
        }
    ]
    
    embeddings = np.array([chunk['embedding'] for chunk in chunks])
    temp_vector_store.add_chunks(chunks, embeddings)
    
    assert temp_vector_store.get_collection_size() == 2


def test_search(temp_vector_store):
    """Test searching in vector store."""
    # Add some chunks first
    chunks = [
        {
            'text': 'Reinforcement learning is a type of machine learning.',
            'embedding': np.random.rand(768).tolist(),
            'paper_title': 'RL Paper',
            'chunk_index': 0
        }
    ]
    
    embeddings = np.array([chunk['embedding'] for chunk in chunks])
    temp_vector_store.add_chunks(chunks, embeddings)
    
    # Search
    query_embedding = np.random.rand(768)
    results = temp_vector_store.search(query_embedding, top_k=1)
    
    assert isinstance(results, list)


def test_clear_collection(temp_vector_store):
    """Test clearing collection."""
    # Add chunks
    chunks = [
        {
            'text': 'Test chunk.',
            'embedding': np.random.rand(768).tolist()
        }
    ]
    embeddings = np.array([chunk['embedding'] for chunk in chunks])
    temp_vector_store.add_chunks(chunks, embeddings)
    
    assert temp_vector_store.get_collection_size() > 0
    
    # Clear
    temp_vector_store.clear_collection()
    
    assert temp_vector_store.get_collection_size() == 0

