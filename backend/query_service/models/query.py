from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class Document(BaseModel):
    """Model for a retrieved document/chunk"""
    content: str
    metadata: Dict[str, Any]
    score: float
    # Optional id field for compatibility with different DB systems
    id: Optional[str] = None

class QueryRequest(BaseModel):
    """Model for a query request"""
    query: str
    collection_name: str
    top_k: int = Field(5, ge=1, le=20, description="Number of documents to retrieve")
    model: str = Field("gpt-4o", description="LLM model to use for generation")
    # Added optional fields for litellm without breaking compatibility
    temperature: Optional[float] = Field(0.3, ge=0.0, le=1.0, description="Temperature for generation")
    max_tokens: Optional[int] = Field(1000, ge=1, description="Maximum number of tokens to generate")
    additional_params: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    """Model for a query response"""
    query: str
    answer: str
    documents: List[Document]
    model: str