from typing import List, Dict, Any, Optional
import os
import json
import logging
from models.query import QueryResponse, Document
from utils.embedding_utils import get_embeddings
from utils.chroma_utils import query_chromadb
from utils.pinecone_utils import query_pinecone
import litellm
from litellm import completion

# Configure logging
logger = logging.getLogger(__name__)

class RAGController:
    """Controller for RAG operations with LiteLLM integration"""
    
    def __init__(self):
        """Initialize the RAG controller"""
        # Load API keys from environment variables
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")
        
        # Configure LiteLLM
        self._configure_litellm()
        
        # Default model
        self.default_model = "gpt-4o"
        
        logger.info("RAGController initialized successfully")
    
    def _configure_litellm(self):
        """Configure LiteLLM with API keys"""
        # Set API keys
        if self.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.openai_api_key
        
        if self.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.anthropic_api_key
        
        if self.google_api_key:
            os.environ["GOOGLE_API_KEY"] = self.google_api_key
            
        if self.deepseek_api_key:
            os.environ["DEEPSEEK_API_KEY"] = self.deepseek_api_key
            
        if self.perplexity_api_key:
            os.environ["PERPLEXITY_API_KEY"] = self.perplexity_api_key
        
        # Set default configuration
        litellm.drop_params = True  # Drop unsupported params instead of error
        litellm.num_retries = 3     # Retry API calls 3 times
        
        # Optional: Load from config file if exists
        config_path = os.getenv("LITELLM_CONFIG_PATH")
        if config_path and os.path.exists(config_path):
            try:
                litellm.config_path = config_path
                logger.info(f"Loaded LiteLLM config from {config_path}")
            except Exception as e:
                logger.error(f"Error loading LiteLLM config: {str(e)}")
    
    def _format_model_name(self, model_name: str) -> str:
        """
        Format model name correctly for litellm
        
        Args:
            model_name: Original model name
            
        Returns:
            Formatted model name for litellm
        """
        # DeepSeek models need "deepseek/" prefix
        if "deepseek" in model_name.lower() and not model_name.startswith("deepseek/"):
            return f"deepseek/{model_name}"
            
        # Perplexity models need "perplexity/" prefix
        if ("pplx" in model_name.lower() or "sonar" in model_name.lower() or "perplexity" in model_name.lower()) and not model_name.startswith("perplexity/"):
            return f"perplexity/{model_name}"
            
        # Google models need "google/" prefix 
        if "gemini" in model_name.lower() and not model_name.startswith("google/"):
            return f"google/{model_name}"
            
        # Return original name for models that don't need special formatting
        return model_name
    
    def search_vector_db(
        self,
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
        try:
            # Generate embeddings for query
            query_embedding = get_embeddings(query)
            
            # Query the appropriate vector database
            if db_type.lower() == "chromadb":
                return query_chromadb(query, query_embedding, collection_name, top_k)
            elif db_type.lower() == "faiss":
                try:
                    from utils.faiss_utils import query_faiss
                    return query_faiss(query, query_embedding, collection_name, top_k)
                except ImportError:
                    logger.error("FAISS utils not available")
                    return []
            elif db_type.lower() == "pinecone":
                return query_pinecone(query, query_embedding, collection_name, top_k)
            else:
                raise ValueError(f"Unsupported vector database: {db_type}")
        except Exception as e:
            logger.error(f"Error searching vector database: {str(e)}")
            # Return empty list on error
            return []
    
    def generate_rag_response(
        self,
        query: str,
        docs: List[Document],
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        additional_params: Dict[str, Any] = None
    ) -> QueryResponse:
        """
        Generate a RAG response using retrieved documents with LiteLLM
        
        Args:
            query: User query
            docs: Retrieved documents from vector database
            model: Model to use (defaults to gpt-4o if not specified)
            temperature: Temperature parameter for generation
            max_tokens: Maximum number of tokens to generate
            additional_params: Additional model-specific parameters
            
        Returns:
            QueryResponse with generated answer and source documents
        """
        # Use default model if none specified
        model_name = model if model else self.default_model
        
        # Format model name for litellm
        formatted_model = self._format_model_name(model_name)
        
        logger.info(f"Using model: {model_name} (formatted as {formatted_model})")
        
        if not docs:
            return QueryResponse(
                query=query,
                answer="No relevant documents found to answer your query.",
                documents=[],
                model=model_name
            )
        
        # Prepare context from retrieved documents
        context = "\n\n".join([f"Document {i+1}:\n{doc.content}" for i, doc in enumerate(docs)])
        
        # Prepare the prompt for RAG
        system_message = "You are a helpful assistant that provides accurate information based on the context provided."
        
        user_message = f"""
Context:
{context}

User Query: {query}

Please answer the query based ONLY on the information provided in the context. If the context doesn't contain relevant information to answer the query, state that you don't have enough information and suggest what might help.
"""
        
        # Prepare messages for chat completion
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        # Prepare parameters
        params = {
            "model": formatted_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        # Add additional parameters
        if additional_params:
            params.update(additional_params)
        
        try:
            logger.info(f"Generating RAG response with model: {formatted_model}")
            
            # Handle missing API keys with mock responses
            if ("gpt" in model_name.lower() or "openai" in model_name.lower()) and not self.openai_api_key:
                logger.warning(f"OpenAI API key not set. Using mock response for model: {model_name}")
                return QueryResponse(
                    query=query,
                    answer="This is a mock response because no valid API key was found. In a real environment, this would be an answer based on the document content.",
                    documents=docs,
                    model=model_name
                )
            
            if ("claude" in model_name.lower() or "anthropic" in model_name.lower()) and not self.anthropic_api_key:
                logger.warning(f"Anthropic API key not set. Using mock response for model: {model_name}")
                return QueryResponse(
                    query=query,
                    answer="This is a mock response because no valid API key was found. In a real environment, this would be an answer based on the document content.",
                    documents=docs,
                    model=model_name
                )
                
            if ("deepseek" in model_name.lower()) and not self.deepseek_api_key:
                logger.warning(f"DeepSeek API key not set. Using mock response for model: {model_name}")
                return QueryResponse(
                    query=query,
                    answer="This is a mock response because no valid DeepSeek API key was found. In a real environment, this would be an answer based on the document content.",
                    documents=docs,
                    model=model_name
                )
                
            if ("perplexity" in model_name.lower() or "pplx" in model_name.lower() or "sonar" in model_name.lower()) and not self.perplexity_api_key:
                logger.warning(f"Perplexity API key not set. Using mock response for model: {model_name}")
                return QueryResponse(
                    query=query,
                    answer="This is a mock response because no valid Perplexity API key was found. In a real environment, this would be an answer based on the document content.",
                    documents=docs,
                    model=model_name
                )
            
            # Call LiteLLM
            response = completion(**params)
            
            # Extract answer
            answer = response.choices[0].message.content
            
            return QueryResponse(
                query=query,
                answer=answer,
                documents=docs,
                model=model_name
            )
            
        except Exception as e:
            logger.error(f"Error generating RAG response: {str(e)}")
            
            # Return error response
            return QueryResponse(
                query=query,
                answer=f"Error generating response: {str(e)}. This is a fallback response.",
                documents=docs,
                model=model_name
            )
    
    def process_rag_request(
        self,
        query: str,
        collection_name: str,
        db_type: str = "chromadb",
        top_k: int = 5,
        model: str = None,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        additional_params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process a complete RAG request
        
        Args:
            query: User query
            collection_name: Name of the collection to query
            db_type: Type of vector database to query
            top_k: Number of results to return
            model: Model to use
            temperature: Temperature parameter for generation
            max_tokens: Maximum number of tokens to generate
            additional_params: Additional model-specific parameters
            
        Returns:
            Dict containing query response and metadata
        """
        try:
            # Search vector database
            docs = self.search_vector_db(query, db_type, collection_name, top_k)
            
            # Generate response
            response = self.generate_rag_response(
                query=query,
                docs=docs,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                additional_params=additional_params
            )
            
            # Format response
            return {
                "query": query,
                "answer": response.answer,
                "documents": [{"id": getattr(doc, "id", ""), "content": doc.content, "metadata": doc.metadata, "score": doc.score} for doc in response.documents],
                "model": response.model,
                "collection_name": collection_name,
                "db_type": db_type,
                "top_k": top_k
            }
            
        except Exception as e:
            logger.error(f"Error processing RAG request: {str(e)}")
            
            # Return error response
            return {
                "query": query,
                "answer": f"Error processing request: {str(e)}",
                "documents": [],
                "model": model if model else self.default_model,
                "collection_name": collection_name,
                "db_type": db_type,
                "top_k": top_k,
                "error": str(e)
            }
    
    def list_models(self) -> List[Dict[str, str]]:
        """
        List available LLM models for RAG
        
        Returns:
            List of model objects with id, provider, and description
        """
        models_info = []
        
        # Add OpenAI models
        if self.openai_api_key:
            models_info.extend([
                {"id": "gpt-4o", "provider": "openai", "description": "OpenAI GPT-4o"},
                {"id": "gpt-4-turbo", "provider": "openai", "description": "OpenAI GPT-4 Turbo"},
                {"id": "gpt-4", "provider": "openai", "description": "OpenAI GPT-4"},
                {"id": "gpt-3.5-turbo", "provider": "openai", "description": "OpenAI GPT-3.5 Turbo"}
            ])
        
        # Add Anthropic models
        if self.anthropic_api_key:
            models_info.extend([
                {"id": "claude-3-opus-20240229", "provider": "anthropic", "description": "Anthropic Claude 3 Opus"},
                {"id": "claude-3-sonnet-20240229", "provider": "anthropic", "description": "Anthropic Claude 3 Sonnet"},
                {"id": "claude-3-haiku-20240307", "provider": "anthropic", "description": "Anthropic Claude 3 Haiku"},
                {"id": "claude-3.5-sonnet-20240620", "provider": "anthropic", "description": "Anthropic Claude 3.5 Sonnet"},
                {"id": "claude-3.7-sonnet-20250219", "provider": "anthropic", "description": "Anthropic Claude 3.7 Sonnet"}
            ])
        
        # Add DeepSeek models
        if self.deepseek_api_key:
            models_info.extend([
                {"id": "deepseek-coder", "provider": "deepseek", "description": "DeepSeek Coder"},
                {"id": "deepseek-llm-67b-chat", "provider": "deepseek", "description": "DeepSeek LLM 67B Chat"},
                {"id": "deepseek-llm-7b-chat", "provider": "deepseek", "description": "DeepSeek LLM 7B Chat"}
            ])
            
        # Add Perplexity models
        if self.perplexity_api_key:
            models_info.extend([
                {"id": "pplx-7b-online", "provider": "perplexity", "description": "Perplexity 7B Online"},
                {"id": "pplx-70b-online", "provider": "perplexity", "description": "Perplexity 70B Online"},
                {"id": "pplx-7b-chat", "provider": "perplexity", "description": "Perplexity 7B Chat"},
                {"id": "pplx-70b-chat", "provider": "perplexity", "description": "Perplexity 70B Chat"},
                {"id": "sonar-small-online", "provider": "perplexity", "description": "Perplexity Sonar Small Online"},
                {"id": "sonar-medium-online", "provider": "perplexity", "description": "Perplexity Sonar Medium Online"}
            ])
        
        # Add Google models
        if self.google_api_key:
            models_info.extend([
                {"id": "gemini-1.5-pro", "provider": "google", "description": "Google Gemini 1.5 Pro"},
                {"id": "gemini-1.5-flash", "provider": "google", "description": "Google Gemini 1.5 Flash"}
            ])
        
        # Always include at least one model from each provider for display purposes
        if not models_info:
            models_info.extend([
                {"id": "gpt-4o", "provider": "openai", "description": "OpenAI GPT-4o (Mock)"},
                {"id": "claude-3-7-sonnet-20250219", "provider": "anthropic", "description": "Anthropic Claude 3.7 Sonnet (Mock)"},
                {"id": "gemini-1.5-pro", "provider": "google", "description": "Google Gemini 1.5 Pro (Mock)"},
                {"id": "deepseek-coder", "provider": "deepseek", "description": "DeepSeek Coder (Mock)"},
                {"id": "pplx-70b-online", "provider": "perplexity", "description": "Perplexity 70B Online (Mock)"}
            ])
        
        return models_info


# For backward compatibility with existing code
def search_vector_db(
    query: str,
    db_type: str,
    collection_name: str,
    top_k: int = 5
) -> List[Document]:
    """
    Backward compatibility function for search_vector_db
    """
    controller = RAGController()
    return controller.search_vector_db(query, db_type, collection_name, top_k)


def generate_rag_response(
    query: str,
    docs: List[Document],
    model: str = "gpt-4o"
) -> QueryResponse:
    """
    Backward compatibility function for generate_rag_response
    """
    controller = RAGController()
    return controller.generate_rag_response(query, docs, model)


def process_rag_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a RAG request from JSON data
    
    Args:
        request_data: Dictionary containing request parameters
        
    Returns:
        Dict containing response data
    """
    # Extract parameters from request data
    query = request_data.get("query")
    collection_name = request_data.get("collection_name")
    db_type = request_data.get("db_type", "chromadb")
    top_k = request_data.get("top_k", 5)
    model = request_data.get("model")
    temperature = request_data.get("temperature", 0.3)
    max_tokens = request_data.get("max_tokens", 1000)
    additional_params = request_data.get("additional_params")
    
    # Validate required parameters
    if not query:
        return {"error": "Query is required"}
    if not collection_name:
        return {"error": "Collection name is required"}
    
    # Process the request
    controller = RAGController()
    return controller.process_rag_request(
        query=query,
        collection_name=collection_name,
        db_type=db_type,
        top_k=top_k,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        additional_params=additional_params
    )

# Provide direct access to model listing
def list_available_models() -> List[Dict[str, str]]:
    """
    List available LLM models for RAG
    
    Returns:
        List of model objects with id, provider, and description
    """
    controller = RAGController()
    return controller.list_models()