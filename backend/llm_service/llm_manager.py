# llm_service/llm_manager.py
import litellm
from litellm import completion
import os
import time
import logging
from .config import GITHUB_CONFIG, AVAILABLE_MODELS, MODEL_MAPPING, MODEL_PRICING

class LLMManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_github_provider()
    
    def setup_github_provider(self):
        """Initialize GitHub models provider"""
        try:
            if not GITHUB_CONFIG["api_key"]:
                self.logger.error("GitHub token not found in environment variables")
                raise ValueError("GitHub token (GITHUB_TOKEN) must be set in environment variables")
            
            litellm.set_provider_config(
                "github",
                {
                    "base_url": GITHUB_CONFIG["base_url"],
                    "api_key": GITHUB_CONFIG["api_key"]
                }
            )
            self.logger.info("GitHub models provider configured successfully")
        except Exception as e:
            self.logger.error(f"Error setting up GitHub provider: {str(e)}")
            raise
    
    def get_available_models(self):
        """Return list of available GitHub models for frontend selection"""
        return AVAILABLE_MODELS
    
    def generate_text(self, model_id, prompt, document_content=None, operation_type="chat"):
        """
        Generic method to generate text using selected GitHub model
        
        Parameters:
        - model_id: ID of the model to use (e.g., "gpt-4o")
        - prompt: User's prompt or instruction
        - document_content: Optional document content for context
        - operation_type: Type of operation (chat, summarize, extract_keypoints)
        
        Returns: Dict with response text, token usage, and cost information
        """
        try:
            # Map the model ID to the LiteLLM format
            model = MODEL_MAPPING.get(model_id)
            if not model:
                raise ValueError(f"Model {model_id} not available through GitHub")
            
            # Create system messages based on operation type
            system_message = self._get_system_message(operation_type)
            
            # Prepare user message with document content if available
            user_message = self._build_user_message(prompt, document_content, operation_type)
            
            # Track processing time
            start_time = time.time()
            
            # Call LiteLLM to generate response
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
            
            response = litellm.completion(
                model=model,
                messages=messages
            )
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Extract and return response details
            result = self._process_response(response, model_id, processing_time)
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating text with {model_id}: {str(e)}")
            raise
    
    def _get_system_message(self, operation_type):
        """Select appropriate system message based on operation type"""
        system_messages = {
            "chat": "You are a helpful assistant that answers questions based on document content.",
            "summarize": "You are a document summarization assistant. Create a comprehensive summary highlighting the key points and main themes.",
            "extract_keypoints": "You are a document analysis assistant. Extract and list the main points, facts, and insights from the document.",
            "default": "You are a helpful assistant."
        }
        return system_messages.get(operation_type, system_messages["default"])
    
    def _build_user_message(self, prompt, document_content, operation_type):
        """Build appropriate user message with document content if available"""
        if document_content:
            if operation_type == "chat":
                return f"Document content:\n\n{document_content}\n\nQuestion: {prompt}"
            elif operation_type == "summarize":
                return f"Please summarize the following document:\n\n{document_content}"
            elif operation_type == "extract_keypoints":
                return f"Extract the key points from this document and present them as a bulleted list:\n\n{document_content}"
            else:
                return f"Document: {document_content}\n\nInstruction: {prompt}"
        else:
            return prompt
    
    def _process_response(self, response, model_id, processing_time):
        """Process the LiteLLM response and calculate costs"""
        # Extract token usage
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        
        # Calculate cost
        cost = self._calculate_cost(model_id, prompt_tokens, completion_tokens)
        
        return {
            "response": response.choices[0].message.content,
            "usage": {
                "input_tokens": prompt_tokens,
                "output_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
                "cost": cost
            },
            "model": model_id,
            "processing_time": processing_time
        }
    
    def _calculate_cost(self, model_id, prompt_tokens, completion_tokens):
        """Calculate the cost based on token usage"""
        if model_id not in MODEL_PRICING:
            return 0
        
        pricing = MODEL_PRICING[model_id]
        input_cost = (prompt_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        
        return round(input_cost + output_cost, 6)