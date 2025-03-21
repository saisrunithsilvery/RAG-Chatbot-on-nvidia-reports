import json
import chromadb
from chromadb.config import Settings
from langchain.embeddings import HuggingFaceEmbeddings
from typing import Optional, List, Dict, Any
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
import os
from langchain.schema import Document

LANGSMITH_API_KEY=os.getenv("LANGSMITH_API_KEY")


# In chromadb.py, modify the load_chunks_into_chroma function:
def load_chunks_into_chroma(
    tmp_path: str, 
    collection_name: str,
    persist_directory: Optional[str] = "./chroma_db",
):
    # Import the Document class
   
    # Load chunks from JSON file
    with open(tmp_path, 'r') as f:
        chunks = json.load(f)
        print(f"Type of result: {type(chunks)}")
        print(f"Structure of result: {chunks[:1] if isinstance(chunks, list) else list(chunks.keys())}")

    # Initialize embeddings
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2") 
    
    # Initialize ChromaDB with the correct API
    persist_directory = "db"
    host = "159.223.100.38"
    port = 8000  
    # Create the vector store using the collection name directly
    client = chromadb.HttpClient(host=host, port=port)
    print(f"Connected to remote ChromaDB at {host}:{port}")
    
    # Create the vector store using the collection name with the remote client
    vector_store = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings
    )
    
    # Convert chunks to Document objects
    documents = []
    for i, chunk in enumerate(chunks):
        # Create metadata dictionary from chunk metadata
        # Extract metadata correctly based on your chunking function's output
        if isinstance(chunk.get("metadata"), dict):
            metadata = chunk["metadata"]
        else:
            # If metadata is not a dict, create a basic metadata dict
            metadata = {
                "source": chunk.get("source", ""),
                "chunk_index": i
            }
        
        # Create Document object with the text from the chunk
        doc = Document(
            page_content=chunk["text"],
            metadata=metadata
        )
        documents.append(doc)
    
    # Add documents to the vector store
    vector_store.add_documents(documents)
    
    # # Persist the collection
    # vector_store.persist()
    
    print(f"Added {len(documents)} chunks to collection '{collection_name}'")
    
    return vector_store