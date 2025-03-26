# Import the Pinecone library
import json
import os
import time
from pinecone import Pinecone
from typing import Optional, List, Dict, Any
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_openai import OpenAIEmbeddings

# Initialize a Pinecone client with 
def load_chunks_into_pinecone(
    tmp_path: str, 
    collection_name: str,
    year: int,
    quarter: int,
    chunk_strategy: Optional[str] = "cluster"

):
    # Load chunks from JSON file
    with open(tmp_path, 'r') as f:
        chunks = json.load(f)
        print(f"Loading chunks into Pinecone collection: {collection_name}")
        print(f"Type of result: {type(chunks)}")
        print(f"Structure of result: {chunks[:1] if isinstance(chunks, list) else list(chunks.keys())}")
    
    # Initialize Pinecone client with API key from environment variable
    pine_cone = os.getenv("PINECONE_API_KEY")
    if not pine_cone:
        raise ValueError("PINECONE_API_KEY environment variable not set")
    pc = Pinecone(api_key=pine_cone)
    
    # Connect to the index
    index = pc.Index(name="test1")
    openai_api_key= os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    # Initialize embedding model
    embedding_model = "text-embedding-3-large"
    embeddings = OpenAIEmbeddings(
            model=embedding_model,
            openai_api_key=openai_api_key
        )
    
    # Prepare vectors for upsert
    vectors_to_upsert = []
    
    if isinstance(chunks, list):
        for i, chunk in enumerate(chunks):
            # Extract the text field
            text_field = chunk.get("text", "")
            
            # Extract metadata if it exists
            metadata = chunk.get("metadata", {})
            
            # COMPLETELY FLATTEN the structure - no nested objects at all
            flat_metadata = {}
            
            # Add year and quarter
            flat_metadata["year"] = year
            flat_metadata["quarter"] = quarter
            
            # Add the text content for searching
            flat_metadata["text"] = text_field
            flat_metadata["chunk_index"] = chunk_strategy
            
            # Flatten all metadata fields
            for key, value in metadata.items():
                # Ensure all values are primitive types (string, number, boolean, or list of strings)
                if isinstance(value, (str, int, float, bool)):
                    flat_metadata[key] = value
                elif isinstance(value, list) and all(isinstance(item, str) for item in value):
                    flat_metadata[key] = value
                else:
                    # Convert any complex types to strings
                    flat_metadata[key] = str(value)
            
            # Generate embedding
            embedding = embeddings.embed_query(text_field)
            doc_prefix = f"{collection_name}_{year}_{quarter}_{int(time.time())}"

            # Then create the chunk ID
            chunk_id = f"{doc_prefix}_chunk_{i}"
            
            vectors_to_upsert.append({
                "id": chunk_id,
                "values": embedding,
                "metadata": flat_metadata  # Completely flattened metadata
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
    
    print(f"Successfully loaded vectors into Pinecone index 'nvidia-collection'")
    return collection_name