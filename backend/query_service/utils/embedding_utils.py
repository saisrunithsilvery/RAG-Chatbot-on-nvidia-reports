from typing import List
from sentence_transformers import SentenceTransformer
import numpy as np
import os

# Initialize the embedding model - use the same model as in chunking.py
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

def get_embeddings(text: str) -> List[float]:
    """
    Generate embeddings for a text using the sentence-transformers model
    
    Args:
        text: Input text to embed
        
    Returns:
        List of float values representing the embedding vector
    """
    # Generate embedding
    embedding = model.encode(text)
    
    # Convert to list of floats (for JSON serialization)
    return embedding.tolist()