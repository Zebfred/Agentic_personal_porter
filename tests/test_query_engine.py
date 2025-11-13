"""
Unit tests for RAG query engine.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import os
from unittest.mock import Mock, patch
from rag_core.query_engine import RAGQueryEngine
from rag_core.vector_store import VectorStore
from rag_core.embeddings import SciBERTEmbedder


@pytest.fixture
def mock_vector_store():
    """Create a mock vector store."""
    store = Mock(spec=VectorStore)
    store.search.return_value = [
        {
            'text': 'Reinforcement learning is a type of machine learning.',
            'metadata': {
                'paper_title': 'Test RL Paper',
                'section_header': 'Introduction'
            },
            'distance': 0.1
        }
    ]
    return store


@pytest.fixture
def mock_embedder():
    """Create a mock embedder."""
    embedder = Mock(spec=SciBERTEmbedder)
    embedder.embed.return_value = [0.1] * 768  # Mock embedding
    return embedder


@patch.dict(os.environ, {'GROQ_API_KEY': 'test_key'})
def test_query_engine_initialization(mock_vector_store, mock_embedder):
    """Test RAGQueryEngine initialization."""
    with patch('rag_core.query_engine.ChatGroq'):
        engine = RAGQueryEngine(
            vector_store=mock_vector_store,
            embedder=mock_embedder
        )
        assert engine.vector_store == mock_vector_store
        assert engine.embedder == mock_embedder


@patch.dict(os.environ, {'GROQ_API_KEY': 'test_key'})
def test_build_context(mock_vector_store, mock_embedder):
    """Test context building."""
    with patch('rag_core.query_engine.ChatGroq'):
        engine = RAGQueryEngine(
            vector_store=mock_vector_store,
            embedder=mock_embedder
        )
        
        chunks = [
            {
                'text': 'First chunk text.',
                'metadata': {
                    'paper_title': 'Paper 1',
                    'section_header': 'Section 1'
                }
            },
            {
                'text': 'Second chunk text.',
                'metadata': {
                    'paper_title': 'Paper 2',
                    'section_header': 'Section 2'
                }
            }
        ]
        
        context = engine._build_context(chunks)
        
        assert 'Paper 1' in context
        assert 'Paper 2' in context
        assert 'First chunk text' in context


@patch.dict(os.environ, {'GROQ_API_KEY': 'test_key'})
def test_construct_prompt(mock_vector_store, mock_embedder):
    """Test prompt construction."""
    with patch('rag_core.query_engine.ChatGroq'):
        engine = RAGQueryEngine(
            vector_store=mock_vector_store,
            embedder=mock_embedder
        )
        
        query = "What is reinforcement learning?"
        context = "Context about RL..."
        
        prompt = engine._construct_prompt(query, context)
        
        assert query in prompt
        assert context in prompt
        assert 'expert' in prompt.lower()


@patch.dict(os.environ, {'GROQ_API_KEY': 'test_key'})
def test_extract_sources(mock_vector_store, mock_embedder):
    """Test source extraction."""
    with patch('rag_core.query_engine.ChatGroq'):
        engine = RAGQueryEngine(
            vector_store=mock_vector_store,
            embedder=mock_embedder
        )
        
        chunks = [
            {
                'text': 'Test text.',
                'metadata': {
                    'paper_title': 'Paper 1',
                    'section_header': 'Section 1'
                },
                'distance': 0.1
            }
        ]
        
        sources = engine._extract_sources(chunks)
        
        assert len(sources) > 0
        assert sources[0]['paper_title'] == 'Paper 1'

