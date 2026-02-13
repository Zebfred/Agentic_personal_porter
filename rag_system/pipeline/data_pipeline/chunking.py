"""
Chunking strategies for splitting documents into smaller pieces.

This module provides:
- Fixed-size chunking: Simple character/token-based splitting with overlap
- FastSemanticChunking: Fast semantic chunking using general-purpose sentence transformers
- ScienceDetailSemanticChunking: Science-focused semantic chunking using SciBERT
"""

from typing import List, Dict, Optional
from pathlib import Path
import re
from sentence_transformers import SentenceTransformer
import numpy as np


class ChunkingStrategy:
    """Base class for chunking strategies."""
    
    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Split text into chunks.
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to include with chunks
            
        Returns:
            List of chunk dictionaries with 'text' and 'metadata' keys
        """
        raise NotImplementedError


class FixedSizeChunking(ChunkingStrategy):
    """Fixed-size chunking with overlap."""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        """
        Initialize fixed-size chunking.
        
        Args:
            chunk_size: Size of each chunk in characters
            overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Split text into fixed-size chunks with overlap.
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to include with chunks
            
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        start = 0
        chunk_index = 0
        
        # Preserve context (title, section) if available
        context_prefix = ""
        if metadata:
            if 'title' in metadata and metadata['title']:
                context_prefix += f"Title: {metadata['title']}\n\n"
            if 'section_header' in metadata and metadata['section_header']:
                context_prefix += f"Section: {metadata['section_header']}\n\n"
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundary near the end
            chunk_text = text[start:end]
            if end < len(text):
                # Look for sentence endings near the chunk boundary
                last_period = chunk_text.rfind('.')
                last_newline = chunk_text.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > self.chunk_size * 0.7:  # Only if not too early
                    end = start + break_point + 1
                    chunk_text = text[start:end]
            
            chunk_text = chunk_text.strip()
            if chunk_text:
                chunk_data = {
                    'text': context_prefix + chunk_text,
                    'chunk_index': chunk_index,
                    'start_char': start,
                    'end_char': end,
                    'chunk_size': len(chunk_text)
                }
                
                if metadata:
                    chunk_data['metadata'] = metadata.copy()
                    chunk_data['metadata']['chunk_index'] = chunk_index
                
                chunks.append(chunk_data)
                chunk_index += 1
            
            # Move start position with overlap
            start = end - self.overlap
            if start >= len(text):
                break
        
        return chunks


class FastSemanticChunking(ChunkingStrategy):
    """Fast semantic chunking using general-purpose sentence transformers."""
    
    def __init__(self, 
                 model_name: str = "all-MiniLM-L6-v2",
                 chunk_size: int = 1000,
                 similarity_threshold: float = 0.5):
        """
        Initialize fast semantic chunking.
        
        Args:
            model_name: Name of sentence transformer model (default: all-MiniLM-L6-v2 for speed)
            chunk_size: Target chunk size in characters
            similarity_threshold: Minimum similarity to keep sentences together
        """
        self.model_name = model_name
        self.chunk_size = chunk_size
        self.similarity_threshold = similarity_threshold
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Lazy load the sentence transformer model."""
        if self.model is None:
            print(f"Loading sentence transformer model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
    
    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Split text into semantically coherent chunks.
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to include with chunks
            
        Returns:
            List of chunk dictionaries
        """
        # Split into sentences
        sentences = self._split_sentences(text)
        
        if not sentences:
            return []
        
        # Generate embeddings for sentences
        embeddings = self.model.encode(sentences, show_progress_bar=False)
        
        # Build chunks based on semantic similarity
        chunks = []
        current_chunk = []
        current_chunk_text = ""
        chunk_index = 0
        
        # Preserve context
        context_prefix = ""
        if metadata:
            if 'title' in metadata and metadata['title']:
                context_prefix += f"Title: {metadata['title']}\n\n"
            if 'section_header' in metadata and metadata['section_header']:
                context_prefix += f"Section: {metadata['section_header']}\n\n"
        
        for i, (sentence, embedding) in enumerate(zip(sentences, embeddings)):
            # If current chunk is empty, start a new one
            if not current_chunk:
                current_chunk.append(sentence)
                current_chunk_text = sentence
                continue
            
            # Calculate similarity with last sentence in current chunk
            last_embedding = embeddings[i - 1] if i > 0 else embedding
            similarity = np.dot(embedding, last_embedding) / (
                np.linalg.norm(embedding) * np.linalg.norm(last_embedding)
            )
            
            # Check if we should start a new chunk
            should_break = (
                similarity < self.similarity_threshold or
                len(current_chunk_text) + len(sentence) > self.chunk_size
            )
            
            if should_break and current_chunk:
                # Save current chunk
                chunk_text = " ".join(current_chunk).strip()
                if chunk_text:
                    chunk_data = {
                        'text': context_prefix + chunk_text,
                        'chunk_index': chunk_index,
                        'num_sentences': len(current_chunk),
                        'chunk_size': len(chunk_text)
                    }
                    
                    if metadata:
                        chunk_data['metadata'] = metadata.copy()
                        chunk_data['metadata']['chunk_index'] = chunk_index
                    
                    chunks.append(chunk_data)
                    chunk_index += 1
                
                # Start new chunk
                current_chunk = [sentence]
                current_chunk_text = sentence
            else:
                # Add to current chunk
                current_chunk.append(sentence)
                current_chunk_text += " " + sentence
        
        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk).strip()
            if chunk_text:
                chunk_data = {
                    'text': context_prefix + chunk_text,
                    'chunk_index': chunk_index,
                    'num_sentences': len(current_chunk),
                    'chunk_size': len(chunk_text)
                }
                
                if metadata:
                    chunk_data['metadata'] = metadata.copy()
                    chunk_data['metadata']['chunk_index'] = chunk_index
                
                chunks.append(chunk_data)
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        # Simple sentence splitting (can be improved with nltk or spacy)
        # Split on sentence endings
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Filter out very short "sentences" (likely false splits)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        return sentences


class ScienceDetailSemanticChunking(ChunkingStrategy):
    """Semantic chunking using SciBERT for scientific papers."""
    
    def __init__(self, 
                 model_name: str = "allenai/scibert_scivocab_uncased",
                 chunk_size: int = 1000,
                 similarity_threshold: float = 0.5):
        """
        Initialize science-focused semantic chunking using SciBERT.
        
        Args:
            model_name: Name of SciBERT model (default: allenai/scibert_scivocab_uncased)
            chunk_size: Target chunk size in characters
            similarity_threshold: Minimum similarity to keep sentences together
        """
        self.model_name = model_name
        self.chunk_size = chunk_size
        self.similarity_threshold = similarity_threshold
        self.model = None
        self.tokenizer = None
        self._load_model()
    
    def _load_model(self):
        """Lazy load the SciBERT model."""
        if self.model is None:
            print(f"Loading SciBERT model: {self.model_name}")
            from transformers import AutoTokenizer, AutoModel
            import torch
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            self.model.to(self.device)
            self.model.eval()
            print(f"SciBERT model loaded on {self.device}")
    
    def _encode_sentences(self, sentences: List[str]) -> np.ndarray:
        """
        Encode sentences using SciBERT.
        
        Args:
            sentences: List of sentence strings
            
        Returns:
            Numpy array of embeddings
        """
        import torch
        
        # Tokenize and encode
        encoded = self.tokenizer(
            sentences,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors='pt'
        )
        
        # Move to device
        encoded = {k: v.to(self.device) for k, v in encoded.items()}
        
        # Generate embeddings
        with torch.no_grad():
            outputs = self.model(**encoded)
            # Use mean pooling of last hidden state
            embeddings = outputs.last_hidden_state.mean(dim=1)
        
        # Move back to CPU and convert to numpy
        return embeddings.cpu().numpy()
    
    def chunk(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Split text into semantically coherent chunks using SciBERT.
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to include with chunks
            
        Returns:
            List of chunk dictionaries
        """
        # Split into sentences
        sentences = self._split_sentences(text)
        
        if not sentences:
            return []
        
        # Generate embeddings for sentences using SciBERT
        embeddings = self._encode_sentences(sentences)
        
        # Build chunks based on semantic similarity
        chunks = []
        current_chunk = []
        current_chunk_text = ""
        chunk_index = 0
        
        # Preserve context
        context_prefix = ""
        if metadata:
            if 'title' in metadata and metadata['title']:
                context_prefix += f"Title: {metadata['title']}\n\n"
            if 'section_header' in metadata and metadata['section_header']:
                context_prefix += f"Section: {metadata['section_header']}\n\n"
        
        for i, (sentence, embedding) in enumerate(zip(sentences, embeddings)):
            # If current chunk is empty, start a new one
            if not current_chunk:
                current_chunk.append(sentence)
                current_chunk_text = sentence
                continue
            
            # Calculate similarity with last sentence in current chunk
            last_embedding = embeddings[i - 1] if i > 0 else embedding
            similarity = np.dot(embedding, last_embedding) / (
                np.linalg.norm(embedding) * np.linalg.norm(last_embedding)
            )
            
            # Check if we should start a new chunk
            should_break = (
                similarity < self.similarity_threshold or
                len(current_chunk_text) + len(sentence) > self.chunk_size
            )
            
            if should_break and current_chunk:
                # Save current chunk
                chunk_text = " ".join(current_chunk).strip()
                if chunk_text:
                    chunk_data = {
                        'text': context_prefix + chunk_text,
                        'chunk_index': chunk_index,
                        'num_sentences': len(current_chunk),
                        'chunk_size': len(chunk_text)
                    }
                    
                    if metadata:
                        chunk_data['metadata'] = metadata.copy()
                        chunk_data['metadata']['chunk_index'] = chunk_index
                    
                    chunks.append(chunk_data)
                    chunk_index += 1
                
                # Start new chunk
                current_chunk = [sentence]
                current_chunk_text = sentence
            else:
                # Add to current chunk
                current_chunk.append(sentence)
                current_chunk_text += " " + sentence
        
        # Add final chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk).strip()
            if chunk_text:
                chunk_data = {
                    'text': context_prefix + chunk_text,
                    'chunk_index': chunk_index,
                    'num_sentences': len(current_chunk),
                    'chunk_size': len(chunk_text)
                }
                
                if metadata:
                    chunk_data['metadata'] = metadata.copy()
                    chunk_data['metadata']['chunk_index'] = chunk_index
                
                chunks.append(chunk_data)
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        # Simple sentence splitting (can be improved with nltk or spacy)
        # Split on sentence endings
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Filter out very short "sentences" (likely false splits)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        return sentences


class DocumentChunker:
    """Main class for chunking documents with different strategies."""
    
    def __init__(self, strategy: ChunkingStrategy):
        """
        Initialize document chunker.
        
        Args:
            strategy: Chunking strategy to use
        """
        self.strategy = strategy
    
    def chunk_document(self, 
                      text: str,
                      title: Optional[str] = None,
                      sections: Optional[List[Dict]] = None) -> List[Dict]:
        """
        Chunk a document, optionally preserving section structure.
        
        Args:
            text: Full document text
            title: Document title
            sections: List of section dictionaries with 'header' and 'content'
            
        Returns:
            List of chunk dictionaries
        """
        chunks = []
        
        if sections:
            # Chunk each section separately to preserve context
            for section in sections:
                section_metadata = {
                    'title': title,
                    'section_header': section.get('header'),
                    'section_index': sections.index(section)
                }
                
                section_chunks = self.strategy.chunk(
                    section.get('content', ''),
                    metadata=section_metadata
                )
                chunks.extend(section_chunks)
        else:
            # Chunk entire document
            metadata = {'title': title} if title else None
            chunks = self.strategy.chunk(text, metadata=metadata)
        
        return chunks
    
    def chunk_extraction_result(self, extraction_result: Dict) -> List[Dict]:
        """
        Chunk a PDF extraction result.
        
        Args:
            extraction_result: Dictionary from PDFExtractor.extract_text()
            
        Returns:
            List of chunk dictionaries
        """
        return self.chunk_document(
            text=extraction_result.get('text', ''),
            title=extraction_result.get('title'),
            sections=extraction_result.get('sections')
        )


def main():
    """Main function for testing chunking."""
    import json
    
    # Load extraction results
    results_file = Path("data/extraction_results.json")
    if not results_file.exists():
        print("No extraction results found. Run pdf_extractor.py first.")
        return
    
    with open(results_file, 'r') as f:
        extraction_results = json.load(f)
    
    # Test all strategies
    print("Testing Fixed-Size Chunking...")
    fixed_chunker = DocumentChunker(FixedSizeChunking(chunk_size=1000, overlap=200))
    
    print("Testing Fast Semantic Chunking...")
    fast_semantic_chunker = DocumentChunker(
        FastSemanticChunking(chunk_size=1000, similarity_threshold=0.5)
    )
    
    print("Testing Science Detail Semantic Chunking (SciBERT)...")
    science_semantic_chunker = DocumentChunker(
        ScienceDetailSemanticChunking(chunk_size=1000, similarity_threshold=0.5)
    )
    
    all_chunks_fixed = []
    all_chunks_fast_semantic = []
    all_chunks_science_semantic = []
    
    for result in extraction_results[:3]:  # Test on first 3 papers
        if 'error' in result:
            continue
        
        print(f"Chunking: {result.get('title', 'Unknown')}")
        
        # Fixed-size chunks
        fixed_chunks = fixed_chunker.chunk_extraction_result(result)
        for chunk in fixed_chunks:
            chunk['paper_title'] = result.get('title')
            chunk['pdf_path'] = result.get('pdf_path')
        all_chunks_fixed.extend(fixed_chunks)
        
        # Fast semantic chunks
        fast_semantic_chunks = fast_semantic_chunker.chunk_extraction_result(result)
        for chunk in fast_semantic_chunks:
            chunk['paper_title'] = result.get('title')
            chunk['pdf_path'] = result.get('pdf_path')
        all_chunks_fast_semantic.extend(fast_semantic_chunks)
        
        # Science detail semantic chunks (SciBERT)
        science_semantic_chunks = science_semantic_chunker.chunk_extraction_result(result)
        for chunk in science_semantic_chunks:
            chunk['paper_title'] = result.get('title')
            chunk['pdf_path'] = result.get('pdf_path')
        all_chunks_science_semantic.extend(science_semantic_chunks)
    
    # Save chunks
    fixed_file = Path("data/chunks_fixed.json")
    with open(fixed_file, 'w') as f:
        json.dump(all_chunks_fixed, f, indent=2, default=str)
    
    fast_semantic_file = Path("data/chunks_fast_semantic.json")
    with open(fast_semantic_file, 'w') as f:
        json.dump(all_chunks_fast_semantic, f, indent=2, default=str)
    
    science_semantic_file = Path("data/chunks_science_semantic.json")
    with open(science_semantic_file, 'w') as f:
        json.dump(all_chunks_science_semantic, f, indent=2, default=str)
    
    print(f"\nFixed-size chunks: {len(all_chunks_fixed)}")
    print(f"Fast semantic chunks: {len(all_chunks_fast_semantic)}")
    print(f"Science detail semantic chunks (SciBERT): {len(all_chunks_science_semantic)}")
    print(f"Chunks saved to {fixed_file}, {fast_semantic_file}, and {science_semantic_file}")


if __name__ == "__main__":
    main()

