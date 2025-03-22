import chromadb
from typing import List, Dict, Any
from models.query import Document
import os

# Initialize ChromaDB client - using the same connection details as in chromadb.py
host = "159.223.100.38"  # Update with your actual ChromaDB host
port = 8000  # Update with your actual ChromaDB port
client = chromadb.HttpClient(host=host, port=port)

def list_collections() -> List[str]:
    """
    List all collections in ChromaDB
    
    Returns:
        List of collection names
    """
    collections = client.list_collections()
    return [collection.name for collection in collections]

def query_chromadb(
    query: str,
    query_embedding: List[float],
    collection_name: str,
    top_k: int = 5
) -> List[Document]:
    """
    Query ChromaDB for relevant documents
    
    Args:
        query: Original query text
        query_embedding: Vector embedding of the query
        collection_name: Name of the collection to query
        top_k: Number of results to return
        
    Returns:
        List of Document objects with content and metadata
    """
    try:
        # Get the collection
        collection = client.get_collection(name=collection_name)
        
        # Query the collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        # Process results
        documents = []
        for i in range(len(results["documents"][0])):
            # Convert ChromaDB result to our Document model
            doc = Document(
                content=results["documents"][0][i],
                metadata=results["metadatas"][0][i] if results["metadatas"][0] else {},
                score=1.0 - float(results["distances"][0][i])  # Convert distance to similarity score
            )
            documents.append(doc)
        
        return documents
    except Exception as e:
        raise Exception(f"Error querying ChromaDB: {str(e)}")