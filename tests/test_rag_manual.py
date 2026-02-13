"""
Manual test script for RAG pipeline.

This script tests the complete RAG pipeline with actual data.
Run this after building the index with build_rag_index.py

Usage:
    python test_rag_manual.py
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag_core.query_engine import RAGQueryEngine
from rag_core.vector_store import VectorStore
from rag_core.embeddings import SciBERTEmbedder
import os


def main():
    """Test RAG pipeline manually."""
    print("="*60)
    print("RAG Pipeline Manual Test")
    print("="*60)
    
    # Check for GROQ API key
    if not os.getenv('GROQ_API_KEY'):
        print("\n⚠️  Warning: GROQ_API_KEY not set in environment")
        print("   Set it with: export GROQ_API_KEY='your-key'")
        print("   Or create a .env file with GROQ_API_KEY=your-key")
        return
    
    # Initialize components
    print("\n1. Initializing components...")
    embedder = SciBERTEmbedder()
    vector_store = VectorStore()
    
    # Check if index exists
    collection_size = vector_store.get_collection_size()
    if collection_size == 0:
        print("\n⚠️  Vector store is empty!")
        print("   Run: python build_rag_index.py")
        print("   to build the index first.")
        return
    
    print(f"   ✓ Vector store contains {collection_size} chunks")
    
    # Initialize query engine
    print("\n2. Initializing query engine...")
    engine = RAGQueryEngine(vector_store=vector_store, embedder=embedder)
    print("   ✓ Query engine ready")
    
    # Test queries - Basic Theory
    basic_theory_queries = [
        "What is Q-learning?",
        "Explain the difference between on-policy and off-policy reinforcement learning.",
        "How does the DQN algorithm work?",
        "What is the Bellman equation?",
    ]
    
    # Test queries - Relating Theory to Code Development
    theory_to_code_queries = [
        "How do I implement Q-learning in Python? Show me the code structure.",
        "Write a Python function that implements the Bellman equation update.",
        "How would I code a policy gradient algorithm? What are the key components?",
        "Show me how to implement experience replay buffer in code.",
        "How do I structure a DQN implementation? What classes and methods do I need?",
    ]
    
    # Test queries - Teaching Theory to People of Any Level
    adaptive_teaching_queries = [
        "Explain Q-learning to a complete beginner who has never heard of reinforcement learning.",
        "Explain Q-learning to someone with a computer science degree but no ML background.",
        "Explain Q-learning to a machine learning researcher who wants to understand the mathematical foundations.",
        "Explain the Bellman equation like I'm 10 years old.",
        "Explain policy gradients to a software engineer who understands neural networks but not RL.",
    ]
    
    all_test_queries = [
        ("Basic Theory Queries", basic_theory_queries),
        ("Relating Theory to Code Development", theory_to_code_queries),
        ("Teaching Theory to People of Any Level", adaptive_teaching_queries)
    ]
    
    print("\n3. Testing queries...")
    print("="*60)
    
    total_queries = sum(len(queries) for _, queries in all_test_queries)
    query_counter = 0
    
    for section_name, queries in all_test_queries:
        print(f"\n{'='*60}")
        print(f"SECTION: {section_name.upper()}")
        print('='*60)
        
        for query in queries:
            query_counter += 1
            print(f"\n[Query {query_counter}/{total_queries}]")
            print(f"Question: {query}")
            print("-" * 60)
            
            try:
                result = engine.answer_question(query, top_k=3)
                
                print(f"\nAnswer:\n{result['answer']}")
                
                # Check if answer addresses the query type
                if "code" in query.lower() or "implement" in query.lower() or "python" in query.lower():
                    if "def " not in result['answer'] and "class " not in result['answer']:
                        print("\n  ⚠️  EXPECTED LIMITATION: Answer doesn't contain code.")
                        print("      Current system retrieves theory but doesn't generate code.")
                
                if "beginner" in query.lower() or "10 years old" in query.lower() or "like i'm" in query.lower():
                    if any(word in result['answer'].lower() for word in ["bellman", "gradient", "stochastic", "optimization"]):
                        print("\n  ⚠️  EXPECTED LIMITATION: Answer may be too technical for beginner level.")
                        print("      Current system doesn't adapt complexity to audience level.")
                
                print(f"\nSources ({len(result['sources'])}):")
                for j, source in enumerate(result['sources'], 1):
                    print(f"  {j}. {source['paper_title']}")
                    print(f"     Section: {source['section']}")
                    print(f"     Similarity: {source['similarity_score']:.3f}")
                
                print("\n" + "="*60)
                
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
    
    print("\n✓ All tests completed!")
    print("\nNote: The 'Theory to Code' and 'Adaptive Teaching' sections are expected")
    print("      to show limitations - these require additional features beyond basic RAG.")


if __name__ == "__main__":
    main()

