import json
import os
from pinecone import Pinecone, ServerlessSpec
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

def load_chunks_into_pinecone(
    tmp_path: str,
    index_name: str,
    namespace: Optional[str] = None,
    api_key: Optional[str] = None,
    environment: str = "gcp-starter",
    dimension: int = 384,  # Default for all-MiniLM-L6-v2
    metric: str = "cosine",
    serverless: bool = False,
    cloud: Optional[str] = None,
    region: Optional[str] = None,
    batch_size: int = 100
) -> str:
    """
    Load chunked documents from a JSON file into Pinecone.
    
    Args:
        tmp_path: Path to the JSON file containing chunks
        index_name: Name for the Pinecone index
        namespace: Optional namespace within the index
        api_key: Pinecone API key (defaults to PINECONE_API_KEY env variable)
        environment: Pinecone environment
        dimension: Dimension of the embedding vectors
        metric: Distance metric to use (cosine, dotproduct, or euclidean)
        serverless: Whether to use serverless deployment
        cloud: Cloud provider for serverless (aws or gcp)
        region: Region for serverless deployment
        batch_size: Number of vectors to upsert in each batch
        
    Returns:
        The name of the Pinecone index
    """
    # Load chunks from JSON file
    with open(tmp_path, 'r') as f:
        chunks = json.load(f)
    
    # Check if we have any chunks to process
    if not chunks:
        raise ValueError("No chunks found in the provided file")
    
    # Determine the embedding dimension from the first chunk
    if "embedding" in chunks[0]:
        dimension = len(chunks[0]["embedding"])
        print(f"Using embedding dimension from chunks: {dimension}")
    
    # Get API key from environment if not provided
    if api_key is None:
        api_key = os.environ.get("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("Pinecone API key not found. Please provide api_key or set PINECONE_API_KEY environment variable.")
    
    # Initialize Pinecone client
    pc = Pinecone(api_key=api_key)
    
    # Check if index already exists
    existing_indexes = [index.name for index in pc.list_indexes()]
    
    if index_name not in existing_indexes:
        print(f"Creating new Pinecone index: {index_name}")
        
        # Prepare index creation specs
        if serverless:
            if not cloud or not region:
                raise ValueError("Cloud provider and region must be specified for serverless deployment")
            
            spec = ServerlessSpec(
                cloud=cloud,
                region=region
            )
            
            # Create the index with serverless spec
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric,
                spec=spec
            )
        else:
            # Create the index with standard spec (pod-based)
            pc.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric
            )
        
        print(f"Waiting for index {index_name} to be ready...")
        # No need to wait explicitly, Pinecone V2 handles this automatically
    else:
        print(f"Using existing Pinecone index: {index_name}")
    
    # Connect to the index
    index = pc.Index(index_name)
    
    # Prepare vectors for upserting
    vectors_to_upsert = []
    
    for i, chunk in enumerate(chunks):
        # Generate a unique ID for each chunk
        chunk_id = f"{index_name}_{datetime.now().strftime('%Y%m%d')}_{i}"
        
        # Extract the embedding
        embedding = chunk["embedding"]
        
        # Prepare metadata (exclude the embedding to avoid duplication)
        metadata = {
            "text": chunk["text"],
            **chunk["metadata"]
        }
        
        # Add to vectors list
        vectors_to_upsert.append({
            "id": chunk_id,
            "values": embedding,
            "metadata": metadata
        })
    
    # Upsert in batches
    total_vectors = len(vectors_to_upsert)
    batches = [vectors_to_upsert[i:i + batch_size] for i in range(0, total_vectors, batch_size)]
    
    print(f"Upserting {total_vectors} vectors to Pinecone index '{index_name}' in {len(batches)} batches")
    
    for i, batch in enumerate(batches):
        if namespace:
            index.upsert(vectors=batch, namespace=namespace)
        else:
            index.upsert(vectors=batch)
        print(f"Batch {i+1}/{len(batches)} upserted")
    
    print(f"Successfully added {total_vectors} chunks to Pinecone index '{index_name}'")
    if namespace:
        print(f"Namespace: {namespace}")
    
    return index_name

# Example query function
def query_pinecone(
    index_name: str,
    query_text: str,
    embedding_function,
    top_k: int = 3,
    namespace: Optional[str] = None,
    api_key: Optional[str] = None
):
    """
    Query a Pinecone index with a text string.
    
    Args:
        index_name: Name of the Pinecone index
        query_text: Text to search for
        embedding_function: Function to convert text to an embedding vector
        top_k: Number of results to return
        namespace: Optional namespace to query within
        api_key: Pinecone API key (defaults to PINECONE_API_KEY env variable)
        
    Returns:
        Query results from Pinecone
    """
    # Get API key from environment if not provided
    if api_key is None:
        api_key = os.environ.get("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("Pinecone API key not found. Please provide api_key or set PINECONE_API_KEY environment variable.")
    
    # Initialize Pinecone client
    pc = Pinecone(api_key=api_key)
    
    # Connect to the index
    index = pc.Index(index_name)
    
    # Generate embedding for the query text
    query_embedding = embedding_function(query_text)
    
    # Query the index
    if namespace:
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=namespace,
            include_metadata=True
        )
    else:
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
    
    return results

# Example usage
def example_pinecone_usage():
    # Create a simple embedding function (for demonstration)
    # In practice, you would use your HuggingFace embeddings or another model
    from langchain.embeddings import HuggingFaceEmbeddings
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # Load chunks into Pinecone
    index_name = load_chunks_into_pinecone(
        tmp_path="/path/to/your/tmp_file.json",
        index_name="document-chunks",
        namespace="my-docs",
        # Serverless-specific parameters (if using serverless)
        serverless=True,
        cloud="aws",
        region="us-west-2"
    )
    
    # Example query
    query_text = "What is semantic chunking?"
    results = query_pinecone(
        index_name=index_name,
        query_text=query_text,
        embedding_function=lambda text: embeddings.embed_query(text),
        top_k=3,
        namespace="my-docs"
    )
    
    print("\nQuery:", query_text)
    print("\nResults:")
    for i, match in enumerate(results["matches"]):
        print(f"\nResult {i+1} (Score: {match['score']:.4f}):")
        print(f"Metadata: {match['metadata']}")
        text = match['metadata']['text']
        print(f"Content: {text[:150]}...")  # Show first 150 chars
    
    return results

# Integration with Airflow
def airflow_load_to_pinecone(**kwargs):
    """Function to be used in Airflow DAG"""
    ti = kwargs['ti']
    
    # Get the temporary file path from the previous task
    tmp_file = ti.xcom_pull(task_ids='chunk_document_task')
    
    # Get other parameters
    index_name = ti.xcom_pull(task_ids='process_request', key='pinecone_index', default="document-chunks")
    namespace = ti.xcom_pull(task_ids='process_request', key='pinecone_namespace', default=None)
    
    # Load chunks into Pinecone
    index_name = load_chunks_into_pinecone(
        tmp_path=tmp_file,
        index_name=index_name,
        namespace=namespace
    )
    
    # Return index name for next task
    return index_name