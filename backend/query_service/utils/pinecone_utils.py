import os
from pinecone import Pinecone
from typing import List, Dict, Any
from models.query import Document

# Initialize Pinecone client - using the same API key as in pinecone.py
pine_cone = os.getenv("PINECONE_API_KEY")
pc = Pinecone(api_key=pine_cone)

def list_collections() -> List[str]:
    """
    List all Pinecone indexes
    
    Returns:
        List of index names
    """
    try:
        # Get list of all indexes
        indexes = pc.list_indexes()
        return indexes
    except Exception as e:
        raise Exception(f"Error listing Pinecone indexes: {str(e)}")

def query_pinecone(
    query: str,
    query_embedding: List[float],
    index_name: str,
    top_k: int = 5
) -> List[Document]:
    """
    Query Pinecone for relevant documents
    
    Args:
        query: Original query text
        query_embedding: Vector embedding of the query
        index_name: Name of the Pinecone index
        top_k: Number of results to return
        
    Returns:
        List of Document objects with content and metadata
    """
    try:
        # Sanitize index name to conform to Pinecone naming rules (same as in pinecone.py)
        sanitized_index_name = index_name.replace('_', '-').lower()
        
        # Connect to the index
        index = pc.Index(sanitized_index_name)
        
        # Query the index
        query_results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        
        # Process results
        documents = []
        for match in query_results.matches:
            # Extract text from metadata
            text = match.metadata.get("text", "")
            
            # Remove text from metadata to avoid duplication
            metadata = {k: v for k, v in match.metadata.items() if k != "text"}
            
            doc = Document(
                content=text,
                metadata=metadata,
                score=float(match.score)
            )
            documents.append(doc)
        
        return documents
    except Exception as e:
        raise Exception(f"Error querying Pinecone: {str(e)}")