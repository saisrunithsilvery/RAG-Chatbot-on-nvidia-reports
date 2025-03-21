# Import the Pinecone library
import json
import os
import time
from pinecone import Pinecone
from typing import Optional, List, Dict, Any
from langchain.embeddings import HuggingFaceEmbeddings

# Initialize a Pinecone client with 
def load_chunks_into_pinecone(
    tmp_path: str, 
    collection_name: str
):
    
    
    # Sanitize collection name to conform to Pinecone naming rules
    sanitized_index_name = collection_name.replace('_', '-').lower()
    print(f"Original collection name: {collection_name}, sanitized: {sanitized_index_name}")
    
    # Load chunks from JSON file
    with open(tmp_path, 'r') as f:
        chunks = json.load(f)
        print(f"Type of result: {type(chunks)}")
        print(f"Structure of result: {chunks[:1] if isinstance(chunks, list) else list(chunks.keys())}")
    
    # Initialize Pinecone client with API key from environment variable
    pine_cone = os.getenv("PINECONE_API_KEY")
    if not pine_cone:
        raise ValueError("PINECONE_API_KEY environment variable not set")
    pc = Pinecone(api_key=pine_cone)
    
    # Force delete the existing index if it exists
    try:
        if pc.has_index(sanitized_index_name):
            print(f"Deleting existing index: {sanitized_index_name}")
            pc.delete_index(sanitized_index_name)
            time.sleep(20)  # Wait longer for deletion to complete
    except Exception as e:
        print(f"Error during index deletion: {str(e)}")
        # Continue anyway - we'll try to create a new index
    
    # Define our embedding model and dimension
    embedding_model = "sentence-transformers/all-MiniLM-L6-v2"  # 384 dimensions
    dimension = 384
    
    # Create a new index with the 'spec' parameter
    try:
        print(f"Creating new index: {sanitized_index_name} with dimension: {dimension}")
        
        # Define the spec directly - this version should work with your Pinecone client
        spec = {
            "serverless": {
                "cloud": "aws",
                "region": "us-east-1"
            }
        }
        
        pc.create_index(
            name=sanitized_index_name,
            dimension=dimension,
            metric="cosine",
            spec=spec
        )
        time.sleep(20)  # Wait for creation to complete
    except Exception as e:
        print(f"Error creating index: {str(e)}")
        
        # Let's try an alternative approach if the first one fails
        try:
            print("Trying alternative index creation approach...")
            # Older style spec format
            pc.create_index(
                name=sanitized_index_name,
                dimension=dimension,
                metric="cosine",
                spec={"pod_type": "p1.x1"}  # An alternative spec format
            )
            time.sleep(20)
        except Exception as e2:
            print(f"Alternative approach also failed: {str(e2)}")
            raise e2
    
    # Connect to the index
    index = pc.Index(sanitized_index_name)
    
    # Initialize embedding model
    from langchain.embeddings import HuggingFaceEmbeddings
    embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
    
    # Prepare vectors for upsert
    vectors_to_upsert = []
    
    if isinstance(chunks, list):
        for i, chunk in enumerate(chunks):
            # Define the text field consistently
            text_field = chunk.get("chunk_text") or chunk.get("text", "")
            
            # Generate embedding
            embedding = embeddings.embed_query(text_field)
            
            vectors_to_upsert.append({
                "id": str(chunk.get("id", f"chunk_{i}")),
                "values": embedding,
                "metadata": {
                    "text": text_field,
                    **{k: v for k, v in chunk.items() if k not in ["embedding", "text", "chunk_text"]}
                }
            })
    else:  # If chunks is a dictionary
        for chunk_id, chunk_data in chunks.items():
            # Define the text field consistently
            text_field = chunk_data.get("chunk_text") or chunk_data.get("text", "")
            
            # Generate embedding
            embedding = embeddings.embed_query(text_field)
            
            vectors_to_upsert.append({
                "id": str(chunk_id),
                "values": embedding,
                "metadata": {
                    "text": text_field,
                    **{k: v for k, v in chunk_data.items() if k not in ["embedding", "text", "chunk_text"]}
                }
            })
    
    # Upsert in batches
    batch_size = 100
    total_batches = (len(vectors_to_upsert) + batch_size - 1) // batch_size
    for i in range(0, len(vectors_to_upsert), batch_size):
        batch = vectors_to_upsert[i:i+batch_size]
        try:
            index.upsert(vectors=batch)
            print(f"Upserted batch {i//batch_size + 1}/{total_batches}")
        except Exception as e:
            print(f"Error upserting batch {i//batch_size + 1}: {str(e)}")
            # Continue with the next batch
    
    print(f"Successfully loaded vectors into Pinecone index '{sanitized_index_name}'")
    return sanitized_index_name