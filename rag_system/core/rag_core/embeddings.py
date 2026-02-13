"""
Embedding system using SciBERT for generating embeddings from text chunks.

This module handles:
- Loading SciBERT model
- Generating embeddings for paper chunks
- Batch processing for efficiency
"""

import torch
from transformers import AutoTokenizer, AutoModel
from typing import List, Dict, Optional
import numpy as np
from pathlib import Path


class SciBERTEmbedder:
    """Embedder using SciBERT model for scientific text."""
    
    def __init__(self, model_name: str = "allenai/scibert_scivocab_uncased", device: Optional[str] = None):
        """
        Initialize SciBERT embedder.
        
        Args:
            model_name: HuggingFace model name for SciBERT
            device: Device to run model on ('cuda', 'cpu', or None for auto)
        """
        self.model_name = model_name
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.tokenizer = None
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load SciBERT model and tokenizer."""
        print(f"Loading SciBERT model: {self.model_name}")
        print(f"Using device: {self.device}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()
        
        print("SciBERT model loaded successfully")
    
    def embed(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Numpy array of embedding vector
        """
        return self.embed_batch([text])[0]
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            
        Returns:
            Numpy array of shape (len(texts), embedding_dim)
        """
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            
            # Tokenize
            encoded = self.tokenizer(
                batch_texts,
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
            embeddings = embeddings.cpu().numpy()
            all_embeddings.append(embeddings)
        
        # Concatenate all batches
        result = np.vstack(all_embeddings)
        return result
    
    def embed_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Generate embeddings for a list of text chunks.
        
        Args:
            chunks: List of chunk dictionaries with 'text' key
            
        Returns:
            List of chunks with added 'embedding' key
        """
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.embed_batch(texts)
        
        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk['embedding'] = embedding.tolist()
        
        return chunks
    
    def get_embedding_dim(self) -> int:
        """
        Get the dimension of embeddings produced by this model.
        
        Returns:
            Embedding dimension
        """
        # SciBERT base model has 768 dimensions
        return self.model.config.hidden_size


def main():
    """Main function for testing embeddings."""
    import json
    
    # Load chunks
    chunks_file = Path("data/chunks_fixed.json")
    if not chunks_file.exists():
        print("No chunks found. Run chunking.py first.")
        return
    
    with open(chunks_file, 'r') as f:
        chunks = json.load(f)
    
    print(f"Generating embeddings for {len(chunks)} chunks...")
    
    embedder = SciBERTEmbedder()
    
    # Generate embeddings
    chunks_with_embeddings = embedder.embed_chunks(chunks[:10])  # Test on first 10
    
    # Save results
    output_file = Path("data/chunks_with_embeddings.json")
    with open(output_file, 'w') as f:
        json.dump(chunks_with_embeddings, f, indent=2, default=str)
    
    print(f"Embeddings generated. Results saved to {output_file}")
    print(f"Embedding dimension: {embedder.get_embedding_dim()}")


if __name__ == "__main__":
    main()

