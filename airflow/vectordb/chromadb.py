import os
import json
import logging
import uuid
from typing import List, Dict, Any
import chromadb


logger = logging.getLogger(__name__)

def store_in_chroma(embeddings: List[Dict[str, Any]], 
                   chunked_file_path: str, 
                   quarter: str) -> str:
    """
    Store document embeddings in Chroma vector database.
    
    Args:
        embeddings (List[Dict]): List of embedding dictionaries containing 'text', 'embedding', and 'metadata'
        chunked_file_path (str): Path to the chunked document file
        quarter (str): Quarter information for the document (e.g., 'Q1_2023')
    
    Returns:
        str: Name of the Chroma collection where embeddings were stored
    """
    try:
        # Initialize Chroma client
        chroma_host = os.environ.get("CHROMA_HOST", "localhost")
        chroma_port = os.environ.get("CHROMA_PORT", "8000")
        persistent_dir = os.environ.get("CHROMA_PERSISTENT_DIR", "./chroma_data")
        
        # Determine if we should use HTTP client or persistent client
        if os.environ.get("CHROMA_USE_HTTP", "false").lower() == "true":
            client = chromadb.HttpClient(
                host=chroma_host,
                port=chroma_port
            )
            logger.info(f"Connected to Chroma HTTP server at {chroma_host}:{chroma_port}")
        else:
            client = chromadb.PersistentClient(
                path=persistent_dir
            )
            logger.info(f"Using persistent Chroma client at {persistent_dir}")
        
        # Define collection name using quarter information
        collection_name = f"financial_docs_{quarter.lower()}"
        
        # Check if collection exists, if not create it
        try:
            collection = client.get_collection(name=collection_name)
            logger.info(f"Using existing Chroma collection: {collection_name}")
        except Exception:
            collection = client.create_collection(
                name=collection_name,
                metadata={"quarter": quarter}
            )
            logger.info(f"Created new Chroma collection: {collection_name}")
        
        # Prepare data for insertion
        ids = [str(uuid.uuid4()) for _ in range(len(embeddings))]
        documents = [item["text"] for item in embeddings]
        embedding_vectors = [item["embedding"] for item in embeddings]
        
        # Prepare metadata
        metadatas = []
        for item in embeddings:
            metadata = {
                "quarter": quarter,
                "source": os.path.basename(chunked_file_path)
            }
            
            # Add any additional metadata from the embedding
            if "metadata" in item and isinstance(item["metadata"], dict):
                metadata.update(item["metadata"])
                
            metadatas.append(metadata)
        
        # Add data to collection in batches to avoid memory issues
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            end_idx = min(i + batch_size, len(ids))
            batch_ids = ids[i:end_idx]
            batch_documents = documents[i:end_idx]
            batch_embeddings = embedding_vectors[i:end_idx]
            batch_metadatas = metadatas[i:end_idx]
            
            collection.add(
                ids=batch_ids,
                documents=batch_documents,
                embeddings=batch_embeddings,
                metadatas=batch_metadatas
            )
            logger.info(f"Added batch {i//batch_size + 1} ({len(batch_ids)} items) to Chroma")
        
        # Get collection count to verify
        count = collection.count()
        logger.info(f"Successfully stored {len(embeddings)} embeddings in Chroma collection '{collection_name}' (total count: {count})")
        
        return collection_name
        
    except Exception as e:
        logger.error(f"Error storing embeddings in Chroma: {str(e)}")
        raise