from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class Document(BaseModel):
    """Model for a retrieved document/chunk"""
    content: str
    metadata: Dict[str, Any]
    score: float

class QueryRequest(BaseModel):
    """Model for a query request"""
    query: str
    collection_name: str
    top_k: int = Field(5, ge=1, le=20, description="Number of documents to retrieve")
    model: str = Field("gpt-4o", description="OpenAI model to use for generation")

class QueryResponse(BaseModel):
    """Model for a query response"""
    query: str
    answer: str
    documents: List[Document]
    model: str