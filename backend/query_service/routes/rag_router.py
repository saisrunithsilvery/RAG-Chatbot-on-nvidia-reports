from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from models.query import QueryRequest, QueryResponse
from controllers.rag_controller import search_vector_db, generate_rag_response

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def query_rag(
    request: QueryRequest,
    db_type: Optional[str] = Query("chromadb", description="Vector DB to query (chromadb, faiss, pinecone)")
):
    """
    Query the vector database and generate a response using RAG
    """
    try:
        # Get relevant documents from vector database
        docs = search_vector_db(request.query, db_type, request.collection_name, request.top_k)
        
        # Generate RAG response using retrieved documents
        response = generate_rag_response(request.query, docs, request.model)
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/collections/{db_type}")
async def list_collections(db_type: str = "chromadb"):
    """
    List available collections in the specified vector database
    """
    try:
        # Import the utils based on the db_type
        if db_type == "chromadb":
            from utils.chroma_utils import list_collections as get_collections
        elif db_type == "faiss":
            from utils.faiss_utils import list_collections as get_collections
        elif db_type == "pinecone":
            from utils.pinecone_utils import list_collections as get_collections
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported vector database: {db_type}")
        
        collections = get_collections()
        return {"collections": collections}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))