"""
Test RAG retrieval without LLM (no API key needed).

This script tests the embedding and retrieval components.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag_core.vector_store import VectorStore
from rag_core.embeddings import SciBERTEmbedder


def test_retrieval(collection_name="rl_papers"):
    """Test retrieval with various queries."""
    print("="*70)
    print("RAG Retrieval Test (Embedding + Vector Search)")
    print("="*70)
    
    # Initialize components
    print("\n1. Initializing components...")
    embedder = SciBERTEmbedder()
    vector_store = VectorStore(collection_name=collection_name)
    
    collection_size = vector_store.get_collection_size()
    if collection_size == 0:
        print(f"\n⚠️  Vector store '{collection_name}' is empty!")
        print("   Run: python build_rag_index.py")
        return
    
    print(f"   ✓ Vector store contains {collection_size} chunks")
    
    # Test queries - Basic Theory
    basic_theory_queries = [
        {
            "query": "What is Q-learning?",
            "expected_topics": ["Q-learning", "value function", "Bellman"]
        },
        {
            "query": "How does policy gradient work?",
            "expected_topics": ["policy gradient", "gradient", "policy"]
        },
        {
            "query": "What is the Bellman equation?",
            "expected_topics": ["Bellman", "value", "equation"]
        },
        {
            "query": "Explain actor-critic methods",
            "expected_topics": ["actor", "critic", "policy"]
        },
        {
            "query": "What is experience replay?",
            "expected_topics": ["replay", "buffer", "experience"]
        }
    ]
    
    # Test queries - Relating Theory to Code Development
    theory_to_code_queries = [
        {
            "query": "How do I implement Q-learning in Python? Show me the code structure.",
            "expected_topics": ["Q-learning", "implementation", "code"],
            "category": "Theory to Code"
        },
        {
            "query": "Write a Python function that implements the Bellman equation update.",
            "expected_topics": ["Bellman", "update", "code"],
            "category": "Theory to Code"
        },
        {
            "query": "How would I code a policy gradient algorithm? What are the key components?",
            "expected_topics": ["policy gradient", "implementation", "components"],
            "category": "Theory to Code"
        },
        {
            "query": "Show me how to implement experience replay buffer in code.",
            "expected_topics": ["experience replay", "buffer", "implementation"],
            "category": "Theory to Code"
        },
        {
            "query": "How do I structure a DQN implementation? What classes and methods do I need?",
            "expected_topics": ["DQN", "implementation", "structure"],
            "category": "Theory to Code"
        }
    ]
    
    # Test queries - Teaching Theory to People of Any Level
    adaptive_teaching_queries = [
        {
            "query": "Explain Q-learning to a complete beginner who has never heard of reinforcement learning.",
            "expected_topics": ["Q-learning", "beginner", "explanation"],
            "category": "Adaptive Teaching",
            "level": "beginner"
        },
        {
            "query": "Explain Q-learning to someone with a computer science degree but no ML background.",
            "expected_topics": ["Q-learning", "intermediate", "explanation"],
            "category": "Adaptive Teaching",
            "level": "intermediate"
        },
        {
            "query": "Explain Q-learning to a machine learning researcher who wants to understand the mathematical foundations.",
            "expected_topics": ["Q-learning", "mathematical", "foundations"],
            "category": "Adaptive Teaching",
            "level": "advanced"
        },
        {
            "query": "Explain the Bellman equation like I'm 10 years old.",
            "expected_topics": ["Bellman", "simple", "explanation"],
            "category": "Adaptive Teaching",
            "level": "beginner"
        },
        {
            "query": "Explain policy gradients to a software engineer who understands neural networks but not RL.",
            "expected_topics": ["policy gradient", "neural networks", "explanation"],
            "category": "Adaptive Teaching",
            "level": "intermediate"
        }
    ]
    
    all_test_queries = [
        ("Basic Theory Queries", basic_theory_queries),
        ("Relating Theory to Code Development", theory_to_code_queries),
        ("Teaching Theory to People of Any Level", adaptive_teaching_queries)
    ]
    
    print("\n2. Testing retrieval...")
    print("="*70)
    
    total_tests = sum(len(queries) for _, queries in all_test_queries)
    test_counter = 0
    
    for section_name, test_queries in all_test_queries:
        print(f"\n{'='*70}")
        print(f"SECTION: {section_name.upper()}")
        print('='*70)
        
        for test in test_queries:
            test_counter += 1
            query = test["query"]
            category = test.get("category", "Basic Theory")
            level = test.get("level", "")
            
            print(f"\n[Test {test_counter}/{total_tests}] [{category}]")
            if level:
                print(f"Level: {level}")
            print(f"Query: {query}")
            print("-" * 70)
            
            # Generate query embedding
            query_embedding = embedder.embed(query)
            
            # Search
            results = vector_store.search(query_embedding, top_k=5)
            
            print(f"\nRetrieved {len(results)} chunks:\n")
            
            for j, result in enumerate(results, 1):
                similarity = 1 - result['distance'] if result['distance'] is not None else 0
                paper_title = result['metadata'].get('paper_title', 'Unknown Paper')
                section = result['metadata'].get('section_header', 'Unknown Section')
                text = result['text']
                
                print(f"  [{j}] Similarity: {similarity:.4f}")
                print(f"      Paper: {paper_title}")
                print(f"      Section: {section}")
                print(f"      Text preview: {text[:200]}...")
                print()
            
            # Analysis for expected failures
            if category == "Theory to Code":
                print("  ⚠️  EXPECTED LIMITATION: Current system retrieves theory but")
                print("      doesn't generate code or provide implementation guidance.")
            elif category == "Adaptive Teaching":
                print("  ⚠️  EXPECTED LIMITATION: Current system doesn't adapt explanation")
                print(f"      complexity to {level} level - uses same retrieval for all levels.")
            
            print("="*70)
    
    print("\n✓ Retrieval tests completed!")
    print("\nNote: To test full RAG (with LLM answers), set GROQ_API_KEY and run:")
    print("     python test_rag_manual.py")


if __name__ == "__main__":
    test_retrieval()

