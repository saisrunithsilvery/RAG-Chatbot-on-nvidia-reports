import os
import json
import logging
from typing import List, Dict, Any
import pinecone

logger = logging.getLogger(__name__)

def store_in_pinecone(embeddings: List[Dict[str, Any]], 
                     chunked_file_path: str, 
                     quarter: str) -> str:
    """
    Store document embeddings in Pinecone vector database.
    
    Args:
        embeddings (List[Dict]): List of embedding dictionaries containing 'text', 'embedding', and 'metadata'
        chunked_file_path (str): Path to the chunked document file
        quarter (str): Quarter information for the document (e.g., 'Q1_2023')
    
    Returns:
        str: Name of the Pinecone index where embeddings were stored
    """
    try:
        # Initialize Pinecone client
        pinecone.init(
            api_key=os.environ.get("PINECONE_API_KEY"),
            environment=os.environ.get("PINECONE_ENVIRONMENT")
        )
        
        # Define index name using quarter information
        index_name = f"financial_docs_{quarter.lower()}"
        
        # Check if index exists, if not create it
        if index_name not in pinecone.list_indexes():
            pinecone.create_index(
                name=index_name,
                dimension=len(embeddings[0]["embedding"]),
                metric="cosine"
            )
            logger.info(f"Created new Pinecone index: {index_name}")
        
        # Connect to the index
        index = pinecone.Index(index_name)
        
        # Prepare vectors for upsert
        vectors_to_upsert = []
        for i, item in enumerate(embeddings):
            vector_id = f"{os.path.basename(chunked_file_path)}_{i}"
            vectors_to_upsert.append({
                "id": vector_id,
                "values": item["embedding"],
                "metadata": {
                    "text": item["text"],
                    "quarter": quarter,
                    "source": os.path.basename(chunked_file_path),
                    **item.get("metadata", {})
                }
            })
        
        # Upsert in batches to avoid hitting API limits
        batch_size = 100
        for i in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[i:i + batch_size]
            index.upsert(vectors=batch)
            
        logger.info(f"Successfully stored {len(embeddings)} embeddings in Pinecone index '{index_name}'")
        return index_name
        
    except Exception as e:
        logger.error(f"Error storing embeddings in Pinecone: {str(e)}")
        raise