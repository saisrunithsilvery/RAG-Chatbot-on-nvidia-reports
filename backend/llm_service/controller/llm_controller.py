import os
import uuid
import time
import json
from typing import Dict, Any, List, Generator, Optional
from fastapi import BackgroundTasks
import logging
import litellm
from litellm import completion, acompletion
from dotenv import load_dotenv

load_dotenv()
# Configure logging
logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.set_verbose = True

class LLMController:
    """Controller for LLM interactions using LiteLLM"""
    
    def __init__(self):
        """Initialize the LiteLLM configuration and task storage"""
        # Load API keys from environment variables
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        self.xai_api_key = os.getenv("XAI_API_KEY")  # For Grok models
        
        # Configure LiteLLM
        self._configure_litellm()
        
        # Default model for each provider
        self.default_models = {
            "openai": "gpt-4o",
            "anthropic": "claude-3-7-sonnet-20250219",
            "google": "gemini-1.5-pro",
            "deepseek": "deepseek-coder",
            "xai": "grok-1"
        }
        
        # In-memory task storage
        self.tasks = {}
        
        logger.info("LLMController initialized successfully")
    
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
            
        if self.xai_api_key:
            os.environ["XAI_API_KEY"] = self.xai_api_key
        
        # Set default configuration
        litellm.drop_params = True  # Drop unsupported params instead of error
        litellm.num_retries = 3      # Retry API calls 3 times
        
        # Optional: Load from config file if exists
        config_path = os.getenv("LITELLM_CONFIG_PATH")
        if config_path and os.path.exists(config_path):
            try:
                litellm.config_path = config_path
                logger.info(f"Loaded LiteLLM config from {config_path}")
            except Exception as e:
                logger.error(f"Error loading LiteLLM config: {str(e)}")
    
    def generate(self, prompt: str, model: str = None, max_tokens: int = 1000, 
                temperature: float = 0.7, provider: str = None, 
                additional_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate text using LiteLLM
        
        Args:
            prompt: The input prompt
            model: Model name
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature parameter for generation
            provider: Override provider detection
            additional_params: Additional model-specific parameters
            
        Returns:
            Dict containing generated text and metadata
        """
        # Determine model to use
        model_name = self._get_model_name(model, provider)
        
        # Add a fallback for when API keys are missing
        # Check if this is an OpenAI model but we don't have an API key
        if ("gpt" in model_name.lower() or "openai" in model_name.lower()) and not self.openai_api_key:
            logger.warning(f"OpenAI API key not set. Using mock response for model: {model_name}")
            return {
                "text": "This is a mock summary generated because no valid API key was found. In a real environment, this would be a summary of the provided document.",
                "model": model_name,
                "provider": "mock",
                "finish_reason": "mock_complete",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150
                }
            }
        
        # Similar checks for other providers
        if ("claude" in model_name.lower() or "anthropic" in model_name.lower()) and not self.anthropic_api_key:
            logger.warning(f"Anthropic API key not set. Using mock response for model: {model_name}")
            return {
                "text": "This is a mock summary generated because no valid API key was found. In a real environment, this would be a summary of the provided document.",
                "model": model_name,
                "provider": "mock",
                "finish_reason": "mock_complete",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150
                }
            }
        
        # Prepare parameters
        params = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        # Add additional parameters
        if additional_params:
            params.update(additional_params)
        
        try:
            logger.info(f"Generating text with model: {model_name}")
            response = completion(**params)
            
            # Get model provider
            provider = self._extract_provider(response, model_name)
            
            # Extract and format response
            result = {
                "text": response.choices[0].message.content,
                "model": response.model,
                "provider": provider,
                "finish_reason": response.choices[0].finish_reason
            }
            
            # Add usage information if available
            if hasattr(response, "usage") and response.usage:
                result["usage"] = {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                    "total_tokens": getattr(response.usage, "total_tokens", 0)
                }
            
            logger.info(f"Successfully generated text with provider: {provider}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating text: {str(e)}")
            
            # Provide a fallback response in case of any error
            return {
                "text": f"Error generating response: {str(e)}. This is a fallback response.",
                "model": model_name,
                "provider": "error_fallback",
                "finish_reason": "error",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }
    
    def chat(self, messages: List[Dict[str, str]], model: str = None, max_tokens: int = 1000, 
            temperature: float = 0.7, provider: str = None, 
            additional_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generate chat completions
        
        Args:
            messages: List of message objects with role and content
            model: Model name
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature parameter for generation
            provider: Override provider detection
            additional_params: Additional model-specific parameters
            
        Returns:
            Dict containing generated text and metadata
        """
        # Determine model to use
        model_name = self._get_model_name(model, provider)
        
        # Add a fallback for when API keys are missing
        # Check if this is an OpenAI model but we don't have an API key
        if ("gpt" in model_name.lower() or "openai" in model_name.lower()) and not self.openai_api_key:
            logger.warning(f"OpenAI API key not set. Using mock response for model: {model_name}")
            return {
                "text": "This is a mock response generated because no valid API key was found. In a real environment, this would be an answer based on the document content.",
                "model": model_name,
                "provider": "mock",
                "finish_reason": "mock_complete",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150
                }
            }
        
        # Similar checks for other providers
        if ("claude" in model_name.lower() or "anthropic" in model_name.lower()) and not self.anthropic_api_key:
            logger.warning(f"Anthropic API key not set. Using mock response for model: {model_name}")
            return {
                "text": "This is a mock response generated because no valid API key was found. In a real environment, this would be an answer based on the document content.",
                "model": model_name,
                "provider": "mock",
                "finish_reason": "mock_complete",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150
                }
            }
        
        # Prepare parameters
        params = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        # Add additional parameters
        if additional_params:
            params.update(additional_params)
        
        try:
            logger.info(f"Generating chat completion with model: {model_name}")
            response = completion(**params)
            
            # Get model provider
            provider = self._extract_provider(response, model_name)
            
            # Extract and format response
            result = {
                "text": response.choices[0].message.content,
                "model": response.model,
                "provider": provider,
                "finish_reason": response.choices[0].finish_reason
            }
            
            # Add usage information if available
            if hasattr(response, "usage") and response.usage:
                result["usage"] = {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(response.usage, "completion_tokens", 0),
                    "total_tokens": getattr(response.usage, "total_tokens", 0)
                }
            
            logger.info(f"Successfully generated chat completion with provider: {provider}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating chat completion: {str(e)}")
            
            # Provide a fallback response in case of any error
            return {
                "text": f"Error generating response: {str(e)}. This is a fallback response.",
                "model": model_name,
                "provider": "error_fallback",
                "finish_reason": "error",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }
    
    def stream(self, messages: List[Dict[str, str]], model: str = None, max_tokens: int = 1000, 
              temperature: float = 0.7, provider: str = None, 
              additional_params: Dict[str, Any] = None) -> Generator[str, None, None]:
        """
        Stream responses from LLM models
        
        Args:
            messages: List of message objects with role and content
            model: Model name
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature parameter for generation
            provider: Override provider detection
            additional_params: Additional model-specific parameters
            
        Yields:
            JSON strings with chunks of the response
        """
        # Determine model to use
        model_name = self._get_model_name(model, provider)
        
        # Check if API key is missing for the model type
        if (("gpt" in model_name.lower() or "openai" in model_name.lower()) and not self.openai_api_key) or \
           (("claude" in model_name.lower() or "anthropic" in model_name.lower()) and not self.anthropic_api_key):
            # For streaming with missing API key, yield a mock response in chunks
            logger.warning(f"API key not set for {model_name}. Using mock streaming response.")
            
            # Mock response broken into chunks
            mock_chunks = [
                "This is a mock streaming response ",
                "because no valid API key was found. ",
                "In a real environment, this would be ",
                "a response based on the document content."
            ]
            
            # Yield each chunk
            for chunk in mock_chunks:
                yield json.dumps({
                    "content": chunk,
                    "model": model_name,
                    "provider": "mock"
                })
            
            # We're done
            return
        
        # Prepare parameters
        params = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        
        # Add additional parameters
        if additional_params:
            params.update(additional_params)
        
        try:
            logger.info(f"Streaming response from model: {model_name}")
            
            # Start streaming
            for chunk in completion(**params):
                # Extract content from the chunk
                content = ""
                if chunk.choices and len(chunk.choices) > 0:
                    if hasattr(chunk.choices[0], "delta") and hasattr(chunk.choices[0].delta, "content"):
                        content = chunk.choices[0].delta.content or ""
                
                # Create streamable JSON
                stream_data = {
                    "content": content,
                    "model": model_name,
                    "provider": self._extract_provider(None, model_name)
                }
                
                yield json.dumps(stream_data)
                
        except Exception as e:
            logger.error(f"Error streaming response: {str(e)}")
            yield json.dumps({"error": str(e), "content": "Error generating streaming response."})
    
    def list_models(self) -> List[Dict[str, str]]:
        """
        List all available models
        
        Returns:
            List of model objects with id, provider, and description
        """
        try:
            # Get models from LiteLLM
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
            
            # Add Google models
            if self.google_api_key:
                models_info.extend([
                    {"id": "gemini-1.5-pro", "provider": "google", "description": "Google Gemini 1.5 Pro"},
                    {"id": "gemini-1.5-flash", "provider": "google", "description": "Google Gemini 1.5 Flash"},
                    {"id": "gemini-2.0-pro", "provider": "google", "description": "Google Gemini 2.0 Pro"},
                    {"id": "gemini-2.0-flash", "provider": "google", "description": "Google Gemini 2.0 Flash"}
                ])
            
            # Always include at least one model from each provider for testing
            if not models_info:
                models_info.extend([
                    {"id": "gpt-4o", "provider": "openai", "description": "OpenAI GPT-4o (Mock)"},
                    {"id": "claude-3-7-sonnet-20250219", "provider": "anthropic", "description": "Anthropic Claude 3.7 Sonnet (Mock)"},
                    {"id": "gemini-1.5-pro", "provider": "google", "description": "Google Gemini 1.5 Pro (Mock)"}
                ])
            
            return models_info
            
        except Exception as e:
            logger.error(f"Error listing models: {str(e)}")
            # Return minimal list in case of error
            return [
                {"id": "gpt-4o", "provider": "openai", "description": "OpenAI GPT-4o (Fallback)"}
            ]
    
    def generate_async(self, background_tasks: BackgroundTasks, prompt: str, model: str = None, 
                      max_tokens: int = 1000, temperature: float = 0.7, provider: str = None, 
                      additional_params: Dict[str, Any] = None) -> str:
        """
        Generate text asynchronously
        
        Args:
            background_tasks: FastAPI BackgroundTasks
            prompt: The input prompt
            model: Model name
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature parameter for generation
            provider: Override provider detection
            additional_params: Additional model-specific parameters
            
        Returns:
            Task ID for tracking the async task
        """
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Initialize task in storage
        self.tasks[task_id] = {
            "status": "processing",
            "created_at": time.time(),
            "result": None
        }
        
        # Add generation task to background tasks
        background_tasks.add_task(
            self._generate_async_task,
            task_id=task_id,
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            provider=provider,
            additional_params=additional_params
        )
        
        return task_id
    
    async def _generate_async_task(self, task_id: str, prompt: str, model: str = None, 
                                max_tokens: int = 1000, temperature: float = 0.7, 
                                provider: str = None, additional_params: Dict[str, Any] = None):
        """Background task for async generation"""
        try:
            # Run generation
            result = self.generate(
                prompt=prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                provider=provider,
                additional_params=additional_params
            )
            
            # Update task with result
            self.tasks[task_id] = {
                "status": "completed",
                "created_at": self.tasks[task_id]["created_at"],
                "completed_at": time.time(),
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Async generation error: {str(e)}")
            
            # Update task with error
            self.tasks[task_id] = {
                "status": "failed",
                "created_at": self.tasks[task_id]["created_at"],
                "completed_at": time.time(),
                "error": str(e)
            }
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the status of an async task
        
        Args:
            task_id: The task ID
            
        Returns:
            Dict containing task status and result (if available)
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task ID {task_id} not found")
        
        return self.tasks[task_id]
    
    def _get_model_name(self, model: Optional[str], provider: Optional[str]) -> str:
        """
        Determine the model name to use
        
        Args:
            model: Model name (optional)
            provider: Provider name (optional)
            
        Returns:
            Model name to use with LiteLLM
        """
        # If model is explicitly provided, use it
        if model:
            return model
        
        # If provider is specified, use its default model
        if provider and provider in self.default_models:
            return self.default_models[provider]
        
        # Check for API keys to determine which provider to use
        if self.openai_api_key:
            return self.default_models["openai"]
        elif self.anthropic_api_key:
            return self.default_models["anthropic"]
        elif self.google_api_key:
            return self.default_models["google"]
        elif self.deepseek_api_key:
            return self.default_models["deepseek"]
        elif self.xai_api_key:
            return self.default_models["xai"]
        
        # If no API keys are available, default to OpenAI for mock response
        logger.warning("No LLM API keys configured. Using gpt-4o for mock responses.")
        return "gpt-4o"
    
    def _extract_provider(self, response: Any, model_name: str) -> str:
        """
        Extract provider name from response or model name
        
        Args:
            response: LiteLLM response object
            model_name: Model name used
            
        Returns:
            Provider name
        """
        # Try to extract from response
        if response and hasattr(response, "model"):
            model = response.model.lower()
            
            if "gpt" in model or "openai" in model:
                return "openai"
            elif "claude" in model or "anthropic" in model:
                return "anthropic"
            elif "gemini" in model or "google" in model:
                return "google"
            elif "deepseek" in model:
                return "deepseek"
            elif "grok" in model or "xai" in model:
                return "xai"
        
        # Extract from model name
        model = model_name.lower()
        
        if "gpt" in model or model.startswith("openai/"):
            return "openai"
        elif "claude" in model or model.startswith("anthropic/"):
            return "anthropic"
        elif "gemini" in model or model.startswith("google/"):
            return "google"
        elif "deepseek" in model or model.startswith("deepseek/"):
            return "deepseek"
        elif "grok" in model or model.startswith("xai/"):
            return "xai"
        
        # Default fallback
        return "unknown"