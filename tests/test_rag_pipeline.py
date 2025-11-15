"""
Integration tests for the complete RAG pipeline.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import json
from pathlib import Path
import tempfile
import shutil
from data_pipeline.pdf_extractor import PDFExtractor
from data_pipeline.chunking import DocumentChunker, FixedSizeChunking
from rag_core.embeddings import SciBERTEmbedder
from rag_core.vector_store import VectorStore
from rag_core.query_engine import RAGQueryEngine
import os


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.mark.integration
def test_end_to_end_pipeline(temp_data_dir):
    """
    Test the complete pipeline from text extraction to query answering.
    This is a simplified integration test that doesn't require actual PDFs.
    """
    # Create sample text (simulating extracted PDF text)
    sample_text = """
    Title: Introduction to Reinforcement Learning
    
    Abstract
    Reinforcement learning is a type of machine learning where an agent learns
    to make decisions by interacting with an environment. The agent receives
    rewards or penalties based on its actions and learns to maximize cumulative
    reward over time.
    
    1. Introduction
    Reinforcement learning (RL) is a subfield of machine learning that focuses
    on how intelligent agents should take actions in an environment to maximize
    the notion of cumulative reward. Unlike supervised learning, RL does not
    require labeled input/output pairs, and unlike unsupervised learning, it
    does not require finding hidden structure in unlabeled data.
    
    2. Q-Learning
    Q-learning is a model-free reinforcement learning algorithm. The goal of
    Q-learning is to learn a policy that tells an agent what action to take
    under what circumstances. It does not require a model of the environment
    and can handle problems with stochastic transitions and rewards.
    """
    
    # Step 1: Chunk the text
    chunker = DocumentChunker(FixedSizeChunking(chunk_size=200, overlap=50))
    chunks = chunker.chunk_document(
        text=sample_text,
        title="Introduction to Reinforcement Learning"
    )
    
    assert len(chunks) > 0
    
    # Step 2: Generate embeddings
    embedder = SciBERTEmbedder()
    texts = [chunk['text'] for chunk in chunks]
    embeddings = embedder.embed_batch(texts)
    
    assert embeddings.shape[0] == len(chunks)
    
    # Step 3: Store in vector database
    vector_store = VectorStore(
        collection_name="test_pipeline",
        persist_directory=temp_data_dir
    )
    
    # Add paper metadata to chunks
    for chunk in chunks:
        chunk['paper_title'] = "Introduction to Reinforcement Learning"
    
    vector_store.add_chunks(chunks, embeddings)
    
    assert vector_store.get_collection_size() == len(chunks)
    
    # Step 4: Query
    if os.getenv('GROQ_API_KEY'):
        engine = RAGQueryEngine(vector_store=vector_store, embedder=embedder)
        
        result = engine.answer_question("What is Q-learning?", top_k=2)
        
        assert 'answer' in result
        assert 'sources' in result
        assert len(result['sources']) > 0
    else:
        pytest.skip("GROQ_API_KEY not set, skipping query test")

