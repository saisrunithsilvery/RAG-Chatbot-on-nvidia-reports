from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from typing import Optional, List, Dict, Any
import json

def load_chunks_into_faiss(
    tmp_path: str, 
    index_name: str = "nvidia_index",
    persist_directory: Optional[str] = "./faiss_index"
):
    # Import FAISS
   
    
    # Load chunks from JSON file
    with open(tmp_path, 'r') as f:
        chunks = json.load(f)
        print(f"Type of result: {type(chunks)}")
        print(f"Structure of result: {chunks[:1] if isinstance(chunks, list) else list(chunks.keys())}")

    # Initialize embeddings
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2") 
    
    # Convert chunks to Document objects
    documents = []
    for i, chunk in enumerate(chunks):
        # Create metadata dictionary from chunk metadata
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
    
    # Create FAISS index from documents
    vector_store = FAISS.from_documents(documents, embeddings)
    
    # Save the FAISS index
    vector_store.save_local(persist_directory)
    
    print(f"Added {len(documents)} chunks to FAISS index and saved to {persist_directory}")
    
    return vector_store