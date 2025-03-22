from typing import List, Dict, Any, Optional
from models.query import QueryResponse, Document
import os
from openai import OpenAI
from utils.embedding_utils import get_embeddings
from utils.chroma_utils import query_chromadb
from utils.pinecone_utils import query_pinecone

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def search_vector_db(
    query: str,
    db_type: str,
    collection_name: str,
    top_k: int = 5
) -> List[Document]:
    """
    Search the vector database for relevant documents
    
    Args:
        query: User query
        db_type: Type of vector database to query (chromadb, faiss, pinecone)
        collection_name: Name of the collection to query
        top_k: Number of results to return
        
    Returns:
        List of relevant documents
    """
    # Generate embeddings for query
    query_embedding = get_embeddings(query)
    
    # Query the appropriate vector database
    if db_type.lower() == "chromadb":
        return query_chromadb(query, query_embedding, collection_name, top_k)
    elif db_type.lower() == "faiss":
        return query_faiss(query, query_embedding, collection_name, top_k)
    elif db_type.lower() == "pinecone":
        return query_pinecone(query, query_embedding, collection_name, top_k)
    else:
        raise ValueError(f"Unsupported vector database: {db_type}")

def generate_rag_response(
    query: str,
    docs: List[Document],
    model: str = "gpt-4o"
) -> QueryResponse:
    """
    Generate a RAG response using retrieved documents
    
    Args:
        query: User query
        docs: Retrieved documents from vector database
        model: OpenAI model to use for response generation
        
    Returns:
        QueryResponse with generated answer and source documents
    """
    if not docs:
        return QueryResponse(
            query=query,
            answer="No relevant documents found to answer your query.",
            documents=[],
            model=model
        )
    
    # Prepare context from retrieved documents
    context = "\n\n".join([f"Document {i+1}:\n{doc.content}" for i, doc in enumerate(docs)])
    
    # Prepare the prompt for RAG
    prompt = f"""You are a helpful assistant that provides accurate information based on the context provided.
    
Context:
{context}

User Query: {query}

Please answer the query based ONLY on the information provided in the context. If the context doesn't contain relevant information to answer the query, state that you don't have enough information and suggest what might help.
"""
    
    # Call OpenAI API
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides accurate information based on the context provided."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        answer = response.choices[0].message.content
        
        return QueryResponse(
            query=query,
            answer=answer,
            documents=docs,
            model=model
        )
    except Exception as e:
        raise Exception(f"Error generating response: {str(e)}")