from langchain.text_splitter import RecursiveCharacterTextSplitter, CharacterTextSplitter, TokenTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document
from langchain.document_loaders import WebBaseLoader
from typing import List, Dict, Any
import os
import requests

def chunk_by_character_with_embeddings(url: str, 
                                      chunk_size: int = 1000, 
                                      chunk_overlap: int = 200) -> List[Dict[str, Any]]:
    """
    Downloads a Markdown file from a URL, chunks text using CharacterTextSplitter,
    and converts chunks to embeddings.
    
    This strategy splits text based on character count, which is the simplest approach
    but doesn't account for semantic boundaries.
    
    Args:
        url: URL of the Markdown file
        chunk_size: Maximum size of each chunk
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of dictionaries containing chunk text and embeddings
    """
    # Load the Markdown file from URL
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
            docs = [Document(page_content=content)]
    except Exception as e:
        raise Exception(f"Error loading content from {url}: {e}")
    
    # Initialize the character text splitter
    text_splitter = CharacterTextSplitter(
        separator="\n\n",
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )
    
    # Split the documents
    chunks = text_splitter.split_documents(docs)
    
    # Initialize the embeddings model with HuggingFace
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # Create embeddings for each chunk
    result = []
    for chunk in chunks:
        embedding_vector = embeddings.embed_query(chunk.page_content)
        result.append({
            "text": chunk.page_content,
            "embedding": embedding_vector,
            "metadata": chunk.metadata
        })
    
    return result

def chunk_by_tokens_with_embeddings(url: str, 
                                   chunk_size: int = 500, 
                                   chunk_overlap: int = 50) -> List[Dict[str, Any]]:
    """
    Downloads a Markdown file from a URL, chunks text using TokenTextSplitter,
    and converts chunks to embeddings.
    
    This strategy splits text based on token count, which is more appropriate
    for language models as they process text as tokens.
    
    Args:
        url: URL of the Markdown file
        chunk_size: Maximum number of tokens per chunk
        chunk_overlap: Number of overlapping tokens between chunks
        
    Returns:
        List of dictionaries containing chunk text and embeddings
    """
    # Load the Markdown file from URL
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
            docs = [Document(page_content=content)]
    except Exception as e:
        raise Exception(f"Error loading content from {url}: {e}")
    
    # Initialize the token text splitter
    text_splitter = TokenTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        encoding_name="cl100k_base"  # The encoding used by GPT-4 models
    )
    
    # Split the documents
    chunks = text_splitter.split_documents(docs)
    
    # Initialize the embeddings model with HuggingFace
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # Create embeddings for each chunk
    result = []
    for chunk in chunks:
        embedding_vector = embeddings.embed_query(chunk.page_content)
        result.append({
            "text": chunk.page_content,
            "embedding": embedding_vector,
            "metadata": chunk.metadata
        })
    
    return result

def chunk_recursively_with_embeddings(url: str, 
                                     chunk_size: int = 1000, 
                                     chunk_overlap: int = 200) -> List[Dict[str, Any]]:
    """
    Downloads a Markdown file from a URL, chunks text using RecursiveCharacterTextSplitter,
    and converts chunks to embeddings.
    
    This strategy splits text recursively based on a hierarchy of separators,
    attempting to maintain semantic coherence by respecting document structure.
    
    Args:
        url: URL of the Markdown file
        chunk_size: Maximum size of each chunk
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of dictionaries containing chunk text and embeddings
    """
    # Load the Markdown file from URL
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
            docs = [Document(page_content=content)]
    except Exception as e:
        raise Exception(f"Error loading content from {url}: {e}")
    
    # Initialize the recursive character text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", ", ", " "],  # Order matters: tries first separator, then next, etc.
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )
    
    # Split the documents
    chunks = text_splitter.split_documents(docs)
    
    # Initialize the embeddings model with HuggingFace
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    # Create embeddings for each chunk
    result = []
    for chunk in chunks:
        embedding_vector = embeddings.embed_query(chunk.page_content)
        result.append({
            "text": chunk.page_content,
            "embedding": embedding_vector,
            "metadata": chunk.metadata
        })
    
    return result

# Example usage:
if __name__ == "__main__":
    # Example URL to a Markdown file (GitHub README, documentation, etc.)
    markdown_url = "https://raw.githubusercontent.com/langchain-ai/langchain/master/README.md"
    
    # Get embeddings using different chunking strategies
    character_chunks = chunk_by_character_with_embeddings(markdown_url)
    token_chunks = chunk_by_tokens_with_embeddings(markdown_url)
    recursive_chunks = chunk_recursively_with_embeddings(markdown_url)
    
    print(f"Character-based chunks: {len(character_chunks)}")
    print(f"Token-based chunks: {len(token_chunks)}")
    print(f"Recursive chunks: {len(recursive_chunks)}")
    
    # Print a sample of the first chunk from each method
    print("\nSample from character-based chunks:")
    print(f"Text: {character_chunks[0]['text'][:150]}...")
    print(f"Embedding length: {len(character_chunks[0]['embedding'])}")
    
    print("\nSample from token-based chunks:")
    print(f"Text: {token_chunks[0]['text'][:150]}...")
    print(f"Embedding length: {len(token_chunks[0]['embedding'])}")
    
    print("\nSample from recursive chunks:")
    print(f"Text: {recursive_chunks[0]['text'][:150]}...")
    print(f"Embedding length: {len(recursive_chunks[0]['embedding'])}")