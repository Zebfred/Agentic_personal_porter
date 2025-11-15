"""
Unit tests for embedding system.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import numpy as np
from rag_core.embeddings import SciBERTEmbedder


def test_scibert_embedder_initialization():
    """Test SciBERTEmbedder initialization."""
    embedder = SciBERTEmbedder()
    assert embedder.model is not None
    assert embedder.tokenizer is not None


def test_embed_single_text():
    """Test embedding a single text."""
    embedder = SciBERTEmbedder()
    
    text = "This is a test sentence about reinforcement learning."
    embedding = embedder.embed(text)
    
    assert isinstance(embedding, np.ndarray)
    assert embedding.shape[0] == embedder.get_embedding_dim()


def test_embed_batch():
    """Test embedding a batch of texts."""
    embedder = SciBERTEmbedder()
    
    texts = [
        "First sentence about machine learning.",
        "Second sentence about deep learning.",
        "Third sentence about neural networks."
    ]
    
    embeddings = embedder.embed_batch(texts)
    
    assert embeddings.shape[0] == len(texts)
    assert embeddings.shape[1] == embedder.get_embedding_dim()


def test_embed_chunks():
    """Test embedding chunks."""
    embedder = SciBERTEmbedder()
    
    chunks = [
        {'text': 'First chunk text.'},
        {'text': 'Second chunk text.'},
        {'text': 'Third chunk text.'}
    ]
    
    chunks_with_embeddings = embedder.embed_chunks(chunks)
    
    assert len(chunks_with_embeddings) == len(chunks)
    assert all('embedding' in chunk for chunk in chunks_with_embeddings)


def test_get_embedding_dim():
    """Test getting embedding dimension."""
    embedder = SciBERTEmbedder()
    dim = embedder.get_embedding_dim()
    
    assert isinstance(dim, int)
    assert dim > 0
    # SciBERT should have 768 dimensions
    assert dim == 768

