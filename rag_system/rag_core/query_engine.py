"""
RAG Query Engine for answering questions using retrieved context.

This module handles:
- Retrieving relevant chunks using vector similarity
- Constructing prompts with retrieved context
- Calling LLM to generate answers
- Returning answers with source citations
"""

import os
from typing import Dict, List, Optional
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from rag_core.embeddings import SciBERTEmbedder
from rag_core.vector_store import VectorStore

load_dotenv()


class RAGQueryEngine:
    """Query engine for RAG-based question answering."""
    
    def __init__(self,
                 vector_store: Optional[VectorStore] = None,
                 embedder: Optional[SciBERTEmbedder] = None,
                 llm_model: str = "groq/llama-3.3-70b-versatile"):
        """
        Initialize RAG query engine.
        
        Args:
            vector_store: VectorStore instance (creates new if None)
            embedder: SciBERTEmbedder instance (creates new if None)
            llm_model: Groq model name to use for generation
        """
        self.vector_store = vector_store or VectorStore()
        self.embedder = embedder or SciBERTEmbedder()
        self.llm = ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            model=llm_model,
            temperature=0.1  # Lower temperature for more factual answers
        )
    
    def answer_question(self, query: str, top_k: int = 5) -> Dict:
        """
        Answer a question using RAG.
        
        Args:
            query: Question to answer
            top_k: Number of relevant chunks to retrieve
            
        Returns:
            Dictionary with:
                - answer: Generated answer
                - sources: List of source citations
                - retrieved_chunks: Retrieved context chunks
        """
        # Generate query embedding
        query_embedding = self.embedder.embed(query)
        
        # Retrieve relevant chunks
        retrieved_chunks = self.vector_store.search(query_embedding, top_k=top_k)
        
        if not retrieved_chunks:
            return {
                'answer': "I couldn't find any relevant information in the paper database to answer this question.",
                'sources': [],
                'retrieved_chunks': []
            }
        
        # Build context from retrieved chunks
        context = self._build_context(retrieved_chunks)
        
        # Construct prompt
        prompt = self._construct_prompt(query, context)
        
        # Generate answer
        response = self.llm.invoke(prompt)
        answer = response.content if hasattr(response, 'content') else str(response)
        
        # Extract sources
        sources = self._extract_sources(retrieved_chunks)
        
        return {
            'answer': answer,
            'sources': sources,
            'retrieved_chunks': retrieved_chunks
        }
    
    def _build_context(self, chunks: List[Dict]) -> str:
        """
        Build context string from retrieved chunks.
        
        Args:
            chunks: List of retrieved chunk dictionaries
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            paper_title = chunk['metadata'].get('paper_title', 'Unknown Paper')
            section = chunk['metadata'].get('section_header', 'Unknown Section')
            text = chunk['text']
            
            context_parts.append(
                f"[Source {i}]\n"
                f"Paper: {paper_title}\n"
                f"Section: {section}\n"
                f"Content: {text}\n"
            )
        
        return "\n---\n\n".join(context_parts)
    
    def _construct_prompt(self, query: str, context: str) -> str:
        """
        Construct prompt for LLM with query and context.
        
        Args:
            query: User's question
            context: Retrieved context from papers
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an expert in Reinforcement Learning. Answer the following question using only the information provided in the context below. If the context doesn't contain enough information to answer the question, say so.

Question: {query}

Context from research papers:
{context}

Instructions:
1. Provide a clear, accurate answer based on the context
2. Cite the specific papers and sections you're drawing from (e.g., "According to [Source 1]...")
3. If the context doesn't fully answer the question, acknowledge what information is missing
4. Be precise and technical, but also clear and accessible

Answer:"""
        
        return prompt
    
    def _extract_sources(self, chunks: List[Dict]) -> List[Dict]:
        """
        Extract source citations from retrieved chunks.
        
        Args:
            chunks: List of retrieved chunk dictionaries
            
        Returns:
            List of source dictionaries with paper title, section, and relevance score
        """
        sources = []
        seen_papers = set()
        
        for chunk in chunks:
            paper_title = chunk['metadata'].get('paper_title', 'Unknown Paper')
            section = chunk['metadata'].get('section_header', 'Unknown Section')
            distance = chunk.get('distance', 0)
            
            # Convert distance to similarity score (lower distance = higher similarity)
            similarity = 1 - distance if distance is not None else 0
            
            # Avoid duplicates
            source_key = (paper_title, section)
            if source_key not in seen_papers:
                sources.append({
                    'paper_title': paper_title,
                    'section': section,
                    'similarity_score': similarity,
                    'pdf_path': chunk['metadata'].get('pdf_path')
                })
                seen_papers.add(source_key)
        
        return sources


def main():
    """Main function for testing query engine."""
    print("Initializing RAG Query Engine...")
    engine = RAGQueryEngine()
    
    # Test queries
    test_queries = [
        "What is Q-learning?",
        "Explain the difference between on-policy and off-policy reinforcement learning.",
        "How does the DQN algorithm work?",
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        
        result = engine.answer_question(query, top_k=3)
        
        print(f"\nAnswer:\n{result['answer']}")
        print(f"\nSources:")
        for i, source in enumerate(result['sources'], 1):
            print(f"  {i}. {source['paper_title']} - {source['section']} (similarity: {source['similarity_score']:.3f})")


if __name__ == "__main__":
    main()

