"""
Unit tests for chunking strategies.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from data_pipeline.chunking import (
    FixedSizeChunking,
    FastSemanticChunking,
    ScienceDetailSemanticChunking,
    DocumentChunker
)


def test_fixed_size_chunking_initialization():
    """Test FixedSizeChunking initialization."""
    chunker = FixedSizeChunking(chunk_size=1000, overlap=200)
    assert chunker.chunk_size == 1000
    assert chunker.overlap == 200


def test_fixed_size_chunking_basic():
    """Test basic fixed-size chunking."""
    chunker = FixedSizeChunking(chunk_size=100, overlap=20)
    
    text = "A " * 200  # Create text longer than chunk_size
    chunks = chunker.chunk(text)
    
    assert len(chunks) > 0
    assert all('text' in chunk for chunk in chunks)
    assert all('chunk_index' in chunk for chunk in chunks)


def test_fixed_size_chunking_with_metadata():
    """Test fixed-size chunking with metadata."""
    chunker = FixedSizeChunking(chunk_size=100, overlap=20)
    
    text = "A " * 200
    metadata = {'title': 'Test Paper', 'section_header': 'Introduction'}
    
    chunks = chunker.chunk(text, metadata=metadata)
    
    assert len(chunks) > 0
    assert all('metadata' in chunk for chunk in chunks)
    assert all(chunk['metadata']['title'] == 'Test Paper' for chunk in chunks)


def test_fast_semantic_chunking_initialization():
    """Test FastSemanticChunking initialization."""
    chunker = FastSemanticChunking(
        model_name="all-MiniLM-L6-v2",
        chunk_size=1000,
        similarity_threshold=0.5
    )
    assert chunker.model_name == "all-MiniLM-L6-v2"
    assert chunker.chunk_size == 1000
    assert chunker.similarity_threshold == 0.5


def test_fast_semantic_chunking_basic():
    """Test basic fast semantic chunking."""
    chunker = FastSemanticChunking(
        model_name="all-MiniLM-L6-v2",
        chunk_size=500,
        similarity_threshold=0.3
    )
    
    text = """
    This is the first sentence. This is the second sentence.
    This is the third sentence. This is the fourth sentence.
    This is the fifth sentence. This is the sixth sentence.
    """
    
    chunks = chunker.chunk(text)
    
    assert len(chunks) > 0
    assert all('text' in chunk for chunk in chunks)
    assert all('num_sentences' in chunk for chunk in chunks)


def test_science_detail_semantic_chunking_initialization():
    """Test ScienceDetailSemanticChunking initialization."""
    chunker = ScienceDetailSemanticChunking(
        model_name="allenai/scibert_scivocab_uncased",
        chunk_size=1000,
        similarity_threshold=0.5
    )
    assert chunker.model_name == "allenai/scibert_scivocab_uncased"
    assert chunker.chunk_size == 1000
    assert chunker.similarity_threshold == 0.5


def test_science_detail_semantic_chunking_basic():
    """Test basic science detail semantic chunking."""
    chunker = ScienceDetailSemanticChunking(
        model_name="allenai/scibert_scivocab_uncased",
        chunk_size=500,
        similarity_threshold=0.3
    )
    
    text = """
    Reinforcement learning is a type of machine learning. 
    The agent learns through interaction with the environment.
    Q-learning is a model-free algorithm. 
    Policy gradients optimize the policy directly.
    """
    
    chunks = chunker.chunk(text)
    
    assert len(chunks) > 0
    assert all('text' in chunk for chunk in chunks)
    assert all('num_sentences' in chunk for chunk in chunks)


def test_document_chunker_initialization():
    """Test DocumentChunker initialization."""
    strategy = FixedSizeChunking()
    chunker = DocumentChunker(strategy)
    assert chunker.strategy == strategy


def test_document_chunker_with_sections():
    """Test DocumentChunker with section structure."""
    strategy = FixedSizeChunking(chunk_size=100, overlap=20)
    chunker = DocumentChunker(strategy)
    
    sections = [
        {'header': 'Introduction', 'content': 'A ' * 150},
        {'header': 'Methodology', 'content': 'B ' * 150}
    ]
    
    chunks = chunker.chunk_document(
        text="",
        title="Test Paper",
        sections=sections
    )
    
    assert len(chunks) > 0
    # Check that section headers are preserved
    assert any('Introduction' in chunk.get('text', '') for chunk in chunks)


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v"])
