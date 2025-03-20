import json
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from typing import Optional, List, Dict, Any

def load_chunks_into_chroma(
    tmp_path: str, 
    collection_name: str,
    persist_directory: Optional[str] = "./chroma_db",
) -> chromadb.Collection:
    """
    Load chunked documents from a JSON file into ChromaDB.
    
    Args:
        tmp_path: Path to the JSON file containing chunks
        collection_name: Name for the ChromaDB collection
        persist_directory: Directory to store the ChromaDB data
        embedding_function_name: Type of embedding function to use ('huggingface', 'openai', or 'none')
        model_name: Name of the embedding model (for HuggingFace)
        
    Returns:
        The ChromaDB collection object
    """
    embedding_function_name = "huggingface",
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    # Load chunks from JSON file
    with open(tmp_path, 'r') as f:
        chunks = json.load(f)
    
    # Initialize ChromaDB client
    chroma_client = chromadb.PersistentClient(
        path=persist_directory,
        settings=Settings(anonymized_telemetry=False)
    )
    
    # Set up the embedding function
    if embedding_function_name.lower() == "huggingface":
        ef = embedding_functions.HuggingFaceEmbeddingFunction(
            model_name=model_name
        )

    elif embedding_function_name.lower() == "none":
        # Use pre-computed embeddings from chunks
        ef = None
    else:
        raise ValueError(f"Unknown embedding function type: {embedding_function_name}")
    
    # Create or get collection
    try:
        # Try to get existing collection
        collection = chroma_client.get_collection(name=collection_name, embedding_function=ef)
        print(f"Using existing collection: {collection_name}")
    except ValueError:
        # Create new collection if it doesn't exist
        collection = chroma_client.create_collection(name=collection_name, embedding_function=ef)
        print(f"Created new collection: {collection_name}")
    
    # Prepare data for batch addition
    ids = []
    documents = []
    metadatas = []
    embeddings = []
    
    for i, chunk in enumerate(chunks):
        # Generate a unique ID for each chunk
        chunk_id = f"{collection_name}_{i}"
        ids.append(chunk_id)
        
        # Add document text
        documents.append(chunk["text"])
        
        # Add metadata
        metadatas.append(chunk["metadata"])
        
        # Add embedding if not using an embedding function
        if embedding_function_name.lower() == "none":
            embeddings.append(chunk["embedding"])
    
    # Add chunks to collection
    if embedding_function_name.lower() == "none":
        # Use pre-computed embeddings
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings
        )
    else:
        # Let ChromaDB compute embeddings
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
    
    print(f"Added {len(chunks)} chunks to collection '{collection_name}'")
    return collection

# Example usage
# def example_chromadb_search():
#     # Load chunks into ChromaDB
#     collection = load_chunks_into_chroma(
#         tmp_path="/path/to/your/tmp_file.json",
#         collection_name="document_chunks",
#         persist_directory="./chroma_storage",
#     )
    
#     # Example query
#     query_text = "What is semantic chunking?"
#     results = collection.query(
#         query_texts=[query_text],
#         n_results=3
#     )
    
#     print("\nQuery:", query_text)
#     print("\nResults:")
#     for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
#         print(f"\nResult {i+1}:")
#         print(f"Metadata: {metadata}")
#         print(f"Content: {doc[:150]}...")  # Show first 150 chars
    
#     return results

# # Integration with Airflow
# def airflow_load_to_chroma(**kwargs):
#     """Function to be used in Airflow DAG"""
#     ti = kwargs['ti']
    
#     # Get the temporary file path from the previous task
#     tmp_file = ti.xcom_pull(task_ids='chunk_document_task')
    
#     # Get other parameters
#     collection_name = ti.xcom_pull(task_ids='process_request', key='collection_name', default="document_chunks")
#     persist_dir = ti.xcom_pull(task_ids='process_request', key='chroma_dir', default="./chroma_db")
    
#     # Load chunks into ChromaDB
#     collection = load_chunks_into_chroma(
#         tmp_path=tmp_file,
#         collection_name=collection_name,
#         persist_directory=persist_dir,
#         embedding_function_name="none"  # Use pre-computed embeddings
#     )
    
#     # Return collection name for next task
#     return collection_name