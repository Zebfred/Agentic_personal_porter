"""
Build RAG index from chunked papers.

This script:
1. Loads chunks from JSON files
2. Generates embeddings using SciBERT
3. Stores embeddings in ChromaDB vector store
4. Creates a ready-to-use RAG index

Usage:
    python build_rag_index.py [--chunking-strategy fixed|fast_semantic|science_semantic]
"""

import argparse
import json
from pathlib import Path
import numpy as np
from tqdm import tqdm

from rag_core.embeddings import SciBERTEmbedder
from rag_core.vector_store import VectorStore


def load_chunks(chunk_file: Path) -> list:
    """
    Load chunks from JSON file.
    
    Args:
        chunk_file: Path to chunk JSON file
        
    Returns:
        List of chunk dictionaries
    """
    if not chunk_file.exists():
        raise FileNotFoundError(f"Chunk file not found: {chunk_file}")
    
    with open(chunk_file, 'r') as f:
        chunks = json.load(f)
    
    print(f"Loaded {len(chunks)} chunks from {chunk_file}")
    return chunks


def build_index(chunks: list, 
                collection_name: str = "rl_papers",
                batch_size: int = 32,
                persist_directory: str = "data/chroma_db"):
    """
    Build RAG index from chunks.
    
    Args:
        chunks: List of chunk dictionaries
        collection_name: Name for ChromaDB collection
        batch_size: Batch size for embedding generation
        persist_directory: Directory to persist ChromaDB
    """
    print(f"\n{'='*60}")
    print("Building RAG Index")
    print('='*60)
    
    # Initialize components
    print("\n1. Initializing embedder...")
    embedder = SciBERTEmbedder()
    
    print("\n2. Initializing vector store...")
    vector_store = VectorStore(
        collection_name=collection_name,
        persist_directory=persist_directory
    )
    
    # Clear existing collection if it exists
    if vector_store.get_collection_size() > 0:
        print(f"   Existing collection has {vector_store.get_collection_size()} chunks")
        # For API use, automatically clear (non-interactive)
        # For CLI use, this can be made interactive via a parameter
        import sys
        if sys.stdin.isatty():  # Only prompt if running interactively
            response = input("   Clear existing collection? (y/n): ")
            if response.lower() == 'y':
                vector_store.clear_collection()
        else:
            # Non-interactive: auto-clear for API calls
            print("   Auto-clearing existing collection (non-interactive mode)")
            vector_store.clear_collection()
    
    # Generate embeddings in batches
    print("\n3. Generating embeddings...")
    texts = [chunk['text'] for chunk in chunks]
    
    embeddings_list = []
    for i in tqdm(range(0, len(texts), batch_size), desc="Embedding batches"):
        batch_texts = texts[i:i + batch_size]
        batch_embeddings = embedder.embed_batch(batch_texts, batch_size=batch_size)
        embeddings_list.append(batch_embeddings)
    
    # Concatenate all embeddings
    all_embeddings = np.vstack(embeddings_list)
    print(f"   Generated {all_embeddings.shape[0]} embeddings (dim: {all_embeddings.shape[1]})")
    
    # Add chunks to vector store
    print("\n4. Storing in vector database...")
    vector_store.add_chunks(chunks, all_embeddings)
    
    # Verify
    final_size = vector_store.get_collection_size()
    print(f"\n✓ Index built successfully!")
    print(f"  Collection: {collection_name}")
    print(f"  Total chunks: {final_size}")
    print(f"  Persist directory: {persist_directory}")
    
    return vector_store


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Build RAG index from chunked papers")
    parser.add_argument(
        '--chunking-strategy',
        choices=['fixed', 'fast_semantic', 'science_semantic'],
        default='fixed',
        help='Chunking strategy to use (default: fixed)'
    )
    parser.add_argument(
        '--collection-name',
        default='rl_papers',
        help='ChromaDB collection name (default: rl_papers)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size for embedding generation (default: 32)'
    )
    
    args = parser.parse_args()
    
    # Determine chunk file
    chunk_file_map = {
        'fixed': 'data/chunks_fixed.json',
        'fast_semantic': 'data/chunks_fast_semantic.json',
        'science_semantic': 'data/chunks_science_semantic.json'
    }
    
    chunk_file = Path(chunk_file_map[args.chunking_strategy])
    
    if not chunk_file.exists():
        print(f"Error: Chunk file not found: {chunk_file}")
        print(f"\nAvailable chunk files:")
        data_dir = Path("data")
        for f in data_dir.glob("chunks_*.json"):
            print(f"  - {f}")
        return
    
    # Load chunks
    chunks = load_chunks(chunk_file)
    
    # Build index
    vector_store = build_index(
        chunks,
        collection_name=args.collection_name,
        batch_size=args.batch_size
    )
    
    # Test query
    print("\n5. Testing index with sample query...")
    embedder = SciBERTEmbedder()
    test_query = "What is Q-learning?"
    query_embedding = embedder.embed(test_query)
    
    results = vector_store.search(query_embedding, top_k=3)
    print(f"\nTest query: '{test_query}'")
    print(f"Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"\n  {i}. Similarity: {1 - result['distance']:.4f}")
        print(f"     Paper: {result['metadata'].get('paper_title', 'Unknown')}")
        print(f"     Text: {result['text'][:150]}...")


if __name__ == "__main__":
    main()

