import json
import chromadb
from chromadb.config import Settings
from langchain.embeddings import HuggingFaceEmbeddings
from typing import Optional, List, Dict, Any
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

def load_chunks_into_chroma(
    tmp_path: str, 
    collection_name: str,
    persist_directory: Optional[str] = "./chroma_db",
) -> chromadb.Collection:
   
    # embedding_function_name= HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    # Load chunks from JSON file
    with open(tmp_path, 'r') as f:
        result = json.load(f)
        chunks = result['chunks']

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2") 
    
    # Initialize ChromaDB   
    persist_directory= "db"
    vector_store = Chroma(embedding_function=embeddings, persist_directory=persist_directory)
    collection = vector_store.get_or_create_collection(collection_name)
    
    # Prepare data for insertion
    ids = [str(i) for i in range(len(chunks))]
    texts = [chunk["text"] for chunk in chunks]
    metadatas = [{"source": chunk.get("source", ""), "metadata": json.dumps(chunk.get("metadata", {}))} for chunk in chunks]
    
    # Add documents to the collection
    collection.add_documents(
        documents=texts,
        metadatas=metadatas,
        ids=ids
    )
    
    # Persist the collection
    vector_store.persist()
    
    print(f"Added {len(chunks)} chunks to collection '{collection_name}'")
    
    return collection