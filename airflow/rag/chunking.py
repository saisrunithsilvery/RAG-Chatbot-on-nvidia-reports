from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter, TokenTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document
from langchain.document_loaders import WebBaseLoader
from typing import List, Dict, Any, Optional
import os
import requests
import tempfile
import json
from datetime import datetime

def chunk_document(
    url: str,
    chunking_strategy: str = "recursive",
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    document_metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Main function to chunk a document and generate embeddings using the specified strategy.
    
    Args:
        url: URL or file path of the document
        chunking_strategy: Strategy to use for chunking (character, token, or recursive)
        chunk_size: Maximum size of each chunk
        chunk_overlap: Overlap between chunks
        model_name: Name of the embedding model to use
        document_metadata: Additional metadata to include with each chunk
        
    Returns:
        List of dictionaries containing chunk text, embeddings, and metadata
    """
    # Default metadata if none provided
    if document_metadata is None:
        document_metadata = {}
    
    # Common metadata for all chunks
    common_metadata = {
        "source": url,
        "chunking_strategy": chunking_strategy,
        "chunk_size": chunk_size, 
        "chunk_overlap": chunk_overlap,
        "embedding_model": model_name,
        "processing_timestamp": datetime.now().isoformat(),
        **document_metadata
    }
    
    # Choose chunking strategy
    if chunking_strategy.lower() == "character":
        result = chunk_by_character_with_embeddings(
            url, chunk_size, chunk_overlap, model_name, common_metadata
        )
    elif chunking_strategy.lower() == "token":
        result = chunk_by_tokens_with_embeddings(
            url, chunk_size, chunk_overlap, model_name, common_metadata
        )
    elif chunking_strategy.lower() == "recursive":
        result = chunk_recursively_with_embeddings(
            url, chunk_size, chunk_overlap, model_name, common_metadata
        )
    else:
        raise ValueError(f"Unknown chunking strategy: {chunking_strategy}")
    
    # Save embeddings to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w') as tmp:
        json.dump(result, tmp, default=str)
        tmp_path = tmp.name
    
    print(f"Chunked document into {len(result)} segments using {chunking_strategy} strategy")
    print(f"Saved embeddings to temporary file: {tmp_path}")
    
    return result, tmp_path

def _load_document(url: str) -> List[Document]:
    """Helper function to load document from URL or file path"""
    try:
        # Check if it's a web URL or a local file path
        if url.startswith(('http://', 'https://')):
            # Use WebBaseLoader for web URLs
            loader = WebBaseLoader(url)
            docs = loader.load()
        else:
            # For local file paths, read directly
            with open(url, 'r', encoding='utf-8') as file:
                content = file.read()
            # Extract filename for metadata
            filename = os.path.basename(url)
            docs = [Document(page_content=content, metadata={"source": filename})]
    except Exception as e:
        raise Exception(f"Error loading content from {url}: {e}")
    
    return docs

def chunk_by_character_with_embeddings(
    url: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    common_metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Downloads a document from a URL or file path, chunks text using CharacterTextSplitter,
    and converts chunks to embeddings.
    
    Args:
        url: URL or file path of the document
        chunk_size: Maximum size of each chunk
        chunk_overlap: Overlap between chunks
        model_name: Name of the embedding model to use
        common_metadata: Common metadata to include with each chunk
        
    Returns:
        List of dictionaries containing chunk text and embeddings
    """
    if common_metadata is None:
        common_metadata = {}
    
    # Load the document
    docs = _load_document(url)
    
    # Initialize the character text splitter
    text_splitter = CharacterTextSplitter(
        separator="\n\n",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )
    
    # Split the documents
    chunks = text_splitter.split_documents(docs)
    
    # Initialize the embeddings model
    embeddings = HuggingFaceEmbeddings(model_name=model_name)
    
    # Create embeddings for each chunk
    result = []
    for i, chunk in enumerate(chunks):
        embedding_vector = embeddings.embed_query(chunk.page_content)
        
        # Combine document metadata with common metadata
        chunk_metadata = {
            **chunk.metadata,
            **common_metadata,
            "chunk_index": i,
            "total_chunks": len(chunks)
        }
        
        result.append({
            "text": chunk.page_content,
            "embedding": embedding_vector,
            "metadata": chunk_metadata
        })
    
    return result

def chunk_by_tokens_with_embeddings(
    url: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    common_metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Downloads a document from a URL or file path, chunks text using TokenTextSplitter,
    and converts chunks to embeddings.
    
    Args:
        url: URL or file path of the document
        chunk_size: Maximum number of tokens per chunk
        chunk_overlap: Number of overlapping tokens between chunks
        model_name: Name of the embedding model to use
        common_metadata: Common metadata to include with each chunk
        
    Returns:
        List of dictionaries containing chunk text and embeddings
    """
    if common_metadata is None:
        common_metadata = {}
    
    # Load the document
    docs = _load_document(url)
    
    # Initialize the token text splitter
    text_splitter = TokenTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        encoding_name="cl100k_base"  # The encoding used by GPT-4 models
    )
    
    # Split the documents
    chunks = text_splitter.split_documents(docs)
    
    # Initialize the embeddings model
    embeddings = HuggingFaceEmbeddings(model_name=model_name)
    
    # Create embeddings for each chunk
    result = []
    for i, chunk in enumerate(chunks):
        embedding_vector = embeddings.embed_query(chunk.page_content)
        
        # Combine document metadata with common metadata
        chunk_metadata = {
            **chunk.metadata,
            **common_metadata,
            "chunk_index": i,
            "total_chunks": len(chunks)
        }
        
        result.append({
            "text": chunk.page_content,
            "embedding": embedding_vector,
            "metadata": chunk_metadata
        })
    
    return result

def chunk_recursively_with_embeddings(
    url: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    common_metadata: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Downloads a document from a URL or file path, chunks text using RecursiveCharacterTextSplitter,
    and converts chunks to embeddings.
    
    Args:
        url: URL or file path of the document
        chunk_size: Maximum size of each chunk
        chunk_overlap: Overlap between chunks
        model_name: Name of the embedding model to use
        common_metadata: Common metadata to include with each chunk
        
    Returns:
        List of dictionaries containing chunk text and embeddings
    """
    if common_metadata is None:
        common_metadata = {}
    
    # Load the document
    docs = _load_document(url)
    
    # Initialize the recursive character text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", ", ", " "],  # Order matters
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )
    
    # Split the documents
    chunks = text_splitter.split_documents(docs)
    
    # Initialize the embeddings model
    embeddings = HuggingFaceEmbeddings(model_name=model_name)
    
    # Create embeddings for each chunk
    result = []
    for i, chunk in enumerate(chunks):
        embedding_vector = embeddings.embed_query(chunk.page_content)
        
        # Combine document metadata with common metadata
        chunk_metadata = {
            **chunk.metadata,
            **common_metadata,
            "chunk_index": i,
            "total_chunks": len(chunks)
        }
        
        result.append({
            "text": chunk.page_content,
            "embedding": embedding_vector,
            "metadata": chunk_metadata
        })
    
    return result

# Example usage for Airflow integration
def airflow_chunk_document(**kwargs):
    """Function to be used in Airflow DAG"""
    ti = kwargs['ti']
    
    # Get parameters from previous task
    file_path = ti.xcom_pull(task_ids='process_request', key='file_path')
    chunk_strategy = ti.xcom_pull(task_ids='process_request', key='chunk_strategy')
    chunk_size = ti.xcom_pull(task_ids='process_request', key='chunk_size')
    chunk_overlap = ti.xcom_pull(task_ids='process_request', key='chunk_overlap')
    quarter = ti.xcom_pull(task_ids='process_request', key='quarter')
    
    # Ensure default values if not provided
    if not chunk_strategy:
        chunk_strategy = "recursive"
    if not chunk_size:
        chunk_size = 1000
    if not chunk_overlap:
        chunk_overlap = 200
    
    # Create document metadata
    metadata = {
        "quarter": quarter,
        "processing_date": datetime.now().strftime("%Y-%m-%d")
    }
    
    # Generate embeddings
    embeddings, tmp_file = chunk_document(
        file_path,
        chunking_strategy=chunk_strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        document_metadata=metadata
    )
    
    # Push embeddings to XCom for next task
    ti.xcom_push(key='embeddings', value=embeddings)
    
    # Return the path to the temporary file for next task
    return tmp_file