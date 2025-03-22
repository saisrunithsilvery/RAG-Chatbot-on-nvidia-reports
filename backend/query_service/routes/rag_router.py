from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import Optional, List, Dict, Any
from models.query import QueryRequest, QueryResponse, Document
from controllers.rag_controller import RAGController, search_vector_db, generate_rag_response

# Create new router
router = APIRouter()

# Initialize the RAG controller
rag_controller = RAGController()

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
        
        # If request has temperature and max_tokens, use them with the enhanced controller
        if hasattr(request, 'temperature') and request.temperature is not None or \
           hasattr(request, 'max_tokens') and request.max_tokens is not None or \
           hasattr(request, 'additional_params') and request.additional_params is not None:
            
            # Use the enhanced controller
            response_dict = rag_controller.process_rag_request(
                query=request.query,
                collection_name=request.collection_name,
                db_type=db_type,
                top_k=request.top_k,
                model=request.model,
                temperature=getattr(request, 'temperature', 0.3),
                max_tokens=getattr(request, 'max_tokens', 1000),
                additional_params=getattr(request, 'additional_params', None)
            )
            
            # Convert the documents to the expected format
            documents = []
            for doc in response_dict.get('documents', []):
                if isinstance(doc, dict):
                    # Handle case where document is already a dict
                    documents.append(Document(
                        content=doc.get('content', ''),
                        metadata=doc.get('metadata', {}),
                        score=doc.get('score', 0.0),
                        id=doc.get('id')
                    ))
                else:
                    # Handle case where document is a Document object
                    documents.append(doc)
            
            # Create response object
            response = QueryResponse(
                query=response_dict.get('query', request.query),
                answer=response_dict.get('answer', ''),
                documents=documents,
                model=response_dict.get('model', request.model)
            )
        else:
            # Use the original function for backward compatibility
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
            from utils.embedding_utils import list_collections as get_collections
        elif db_type == "pinecone":
            from utils.pinecone_utils import list_collections as get_collections
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported vector database: {db_type}")
        
        collections = get_collections()
        return {"collections": collections}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @router.get("/models")
# async def list_models():
#     """
#     List available LLM models for RAG
#     """
#     try:
#         # Try to use the LLMController for listing models if available
#         try:
#             from controllers.llm_controller import LLMController
#             llm_controller = LLMController()
#             models = llm_controller.list_models()
#         except ImportError:
#             # Fallback to a basic list if LLMController is not available
#             models = [
#                 {"id": "gpt-4o", "provider": "openai", "description": "OpenAI GPT-4o"},
#                 {"id": "claude-3-7-sonnet-20250219", "provider": "anthropic", "description": "Anthropic Claude 3.7 Sonnet"},
#                 {"id": "gemini-1.5-pro", "provider": "google", "description": "Google Gemini 1.5 Pro"}
#             ]
        
#         return {"models": models}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/rag/raw", response_model=Dict[str, Any])
# async def process_rag_raw(
#     data: Dict[str, Any] = Body(...)
# ):
#     """
#     Process a RAG request with raw JSON data
    
#     Example input:
#     {
#       "query": "What is the summary?",
#       "collection_name": "nvidia_collection",
#       "top_k": 5,
#       "model": "gpt-4o"
#     }
#     """
#     try:
#         # Process the request with the controller
#         response = rag_controller.process_rag_request(
#             query=data.get("query"),
#             collection_name=data.get("collection_name"),
#             db_type=data.get("db_type", "chromadb"),
#             top_k=data.get("top_k", 5),
#             model=data.get("model", "gpt-4o"),
#             temperature=data.get("temperature", 0.3),
#             max_tokens=data.get("max_tokens", 1000),
#             additional_params=data.get("additional_params")
#         )
        
#         return response
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))