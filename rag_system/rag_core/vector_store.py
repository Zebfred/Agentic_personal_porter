"""
Vector database using ChromaDB for storing and retrieving paper chunks.

This module handles:
- Initializing ChromaDB collection
- Storing embeddings with metadata
- Similarity search with configurable top-k
- Persisting database
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from pathlib import Path
import numpy as np


class VectorStore:
    """Vector store using ChromaDB for paper chunks."""
    
    def __init__(self, 
                 collection_name: str = "rl_papers",
                 persist_directory: str = "data/chroma_db"):
        """
        Initialize vector store.
        
        Args:
            collection_name: Name of ChromaDB collection
            persist_directory: Directory to persist ChromaDB data
        """
        self.collection_name = collection_name
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # Use cosine similarity
        )
    
    def add_chunks(self, chunks: List[Dict], embeddings: Optional[np.ndarray] = None):
        """
        Add chunks to the vector store.
        
        Args:
            chunks: List of chunk dictionaries with 'text' and optionally 'embedding'
            embeddings: Optional pre-computed embeddings (if None, chunks must have 'embedding' key)
        """
        if not chunks:
            return
        
        # Extract data
        texts = [chunk['text'] for chunk in chunks]
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        
        # Get embeddings
        if embeddings is not None:
            embeddings_list = embeddings.tolist()
        else:
            embeddings_list = [chunk['embedding'] for chunk in chunks]
        
        # Extract metadata
        metadatas = []
        for chunk in chunks:
            metadata = {}
            if 'paper_title' in chunk:
                metadata['paper_title'] = chunk['paper_title']
            elif 'metadata' in chunk and 'title' in chunk['metadata']:
                metadata['paper_title'] = chunk['metadata']['title']
            
            if 'section_header' in chunk.get('metadata', {}):
                metadata['section_header'] = chunk['metadata']['section_header']
            if 'chunk_index' in chunk:
                metadata['chunk_index'] = chunk['chunk_index']
            if 'pdf_path' in chunk:
                metadata['pdf_path'] = chunk['pdf_path']
            elif 'metadata' in chunk and 'pdf_path' in chunk['metadata']:
                metadata['pdf_path'] = chunk['metadata']['pdf_path']
            metadatas.append(metadata)
        
        # Add to collection
        self.collection.add(
            embeddings=embeddings_list,
            documents=texts,
            ids=ids,
            metadatas=metadatas
        )
        
        print(f"Added {len(chunks)} chunks to vector store")
    
    def search(self, 
               query_embedding: np.ndarray,
               top_k: int = 5,
               filter_dict: Optional[Dict] = None) -> List[Dict]:
        """
        Search for similar chunks.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filter_dict: Optional metadata filters
            
        Returns:
            List of result dictionaries with 'text', 'metadata', and 'distance'
        """
        # Convert embedding to list
        query_embedding_list = query_embedding.tolist() if isinstance(query_embedding, np.ndarray) else query_embedding
        
        # Build where clause for filtering
        where = filter_dict if filter_dict else None
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding_list],
            n_results=top_k,
            where=where
        )
        
        # Format results
        formatted_results = []
        if results['documents'] and len(results['documents'][0]) > 0:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'text': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else None,
                    'id': results['ids'][0][i] if results['ids'] else None
                })
        
        return formatted_results
    
    def search_by_text(self, 
                       query_text: str,
                       query_embedding: np.ndarray,
                       top_k: int = 5,
                       filter_dict: Optional[Dict] = None) -> List[Dict]:
        """
        Search using query text (for convenience).
        
        Args:
            query_text: Query text (for metadata)
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filter_dict: Optional metadata filters
            
        Returns:
            List of result dictionaries
        """
        return self.search(query_embedding, top_k, filter_dict)
    
    def get_collection_size(self) -> int:
        """
        Get the number of chunks in the collection.
        
        Returns:
            Number of chunks
        """
        return self.collection.count()
    
    def clear_collection(self):
        """Clear all chunks from the collection."""
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        print("Collection cleared")


def main():
    """Main function for testing vector store."""
    import json
    from rag_core.embeddings import SciBERTEmbedder
    
    # Load chunks with embeddings
    chunks_file = Path("data/chunks_with_embeddings.json")
    if not chunks_file.exists():
        print("No chunks with embeddings found.")
        print("Generating embeddings first...")
        
        # Load chunks
        chunks_file_raw = Path("data/chunks_fixed.json")
        if not chunks_file_raw.exists():
            print("No chunks found. Run chunking.py first.")
            return
        
        with open(chunks_file_raw, 'r') as f:
            chunks = json.load(f)
        
        # Generate embeddings
        embedder = SciBERTEmbedder()
        chunks = embedder.embed_chunks(chunks[:50])  # Test on first 50
        
        # Save
        with open(chunks_file, 'w') as f:
            json.dump(chunks, f, indent=2, default=str)
    else:
        with open(chunks_file, 'r') as f:
            chunks = json.load(f)
    
    print(f"Loading {len(chunks)} chunks into vector store...")
    
    # Initialize vector store
    vector_store = VectorStore()
    
    # Convert embeddings to numpy array
    embeddings = np.array([chunk['embedding'] for chunk in chunks])
    
    # Add chunks
    vector_store.add_chunks(chunks, embeddings)
    
    print(f"Vector store contains {vector_store.get_collection_size()} chunks")
    
    # Test search
    print("\nTesting search...")
    embedder = SciBERTEmbedder()
    query = "What is Q-learning?"
    query_embedding = embedder.embed(query)
    
    results = vector_store.search(query_embedding, top_k=3)
    
    print(f"\nQuery: {query}")
    print(f"Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Distance: {result['distance']:.4f}")
        print(f"   Paper: {result['metadata'].get('paper_title', 'Unknown')}")
        print(f"   Text: {result['text'][:200]}...")


if __name__ == "__main__":
    main()

