from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging
import json
import asyncio

from controller.llm_controller import LLMController
from utils.redis_utils import RedisManager

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/llm",
    tags=["LLM"],
    responses={404: {"description": "Not found"}},
)

# Request and response models
class Message(BaseModel):
    role: str = Field(..., description="Role of the message sender (system, user, assistant)")
    content: str = Field(..., description="Content of the message")

class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="The prompt to generate text from")
    model: str = Field(None, description="LLM model to use (e.g., gpt-4o, claude-3-opus, gemini-pro)")
    max_tokens: int = Field(1000, description="Maximum number of tokens to generate")
    temperature: float = Field(0.7, description="Temperature parameter for generation")
    provider: str = Field(None, description="Override the provider detection (openai, anthropic, google, etc.)")
    additional_params: Dict[str, Any] = Field({}, description="Additional model-specific parameters")

class ChatRequest(BaseModel):
    messages: List[Message] = Field(..., description="List of messages in the conversation")
    model: str = Field(None, description="LLM model to use")
    max_tokens: int = Field(1000, description="Maximum number of tokens to generate")
    temperature: float = Field(0.7, description="Temperature parameter for generation")
    provider: str = Field(None, description="Override the provider detection")
    additional_params: Dict[str, Any] = Field({}, description="Additional model-specific parameters")

class GenerateResponse(BaseModel):
    text: str = Field(..., description="Generated text")
    model: str = Field(..., description="Model used for generation")
    usage: Optional[Dict[str, Any]] = Field(None, description="Token usage information")
    finish_reason: Optional[str] = Field(None, description="Reason generation finished")
    provider: str = Field(..., description="Provider used for generation")
    price: Optional[Dict[str, float]] = Field(None, description="Cost information for the request")

class ModelInfo(BaseModel):
    id: str = Field(..., description="Model identifier")
    provider: str = Field(..., description="Model provider")
    description: Optional[str] = Field(None, description="Model description")
    input_price_per_1k: Optional[float] = Field(None, description="Price per 1k input tokens in USD")
    output_price_per_1k: Optional[float] = Field(None, description="Price per 1k output tokens in USD")

# Initialize controllers
controller = LLMController()
redis_manager = RedisManager()

# Redis stream setup
LLM_REQUESTS_STREAM = "llm:requests"
LLM_RESPONSES_STREAM = "llm:responses"

# Ensure consumer groups exist
if redis_manager.is_connected():
    redis_manager.stream_create_consumer_group(LLM_REQUESTS_STREAM, "api_group")
    redis_manager.stream_create_consumer_group(LLM_RESPONSES_STREAM, "api_group")

@router.post("/generate/", response_model=GenerateResponse)
async def generate_text(request: GenerateRequest):
    """
    Generate text using any supported LLM model
    """
    try:
        logger.info(f"Processing generation request using model: {request.model or 'default'}")
        
        # Optional: Log request to Redis stream
        if redis_manager.is_connected():
            request_id = redis_manager.stream_add(
                LLM_REQUESTS_STREAM,
                {
                    "type": "generate",
                    "model": request.model or "default",
                    "prompt_preview": request.prompt[:100] + "..." if len(request.prompt) > 100 else request.prompt,
                    "timestamp": asyncio.get_event_loop().time()
                }
            )
        
        result = controller.generate(
            prompt=request.prompt,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            provider=request.provider,
            additional_params=request.additional_params
        )
        
        # Calculate pricing information
        price_info = controller.calculate_price(
            model=result["model"],
            provider=result["provider"],
            usage=result.get("usage", {})
        )
        result["price"] = price_info
        
        # Optional: Log response to Redis stream
        if redis_manager.is_connected():
            redis_manager.stream_add(
                LLM_RESPONSES_STREAM,
                {
                    "type": "generate",
                    "model": result["model"],
                    "response_preview": result["text"][:100] + "..." if len(result["text"]) > 100 else result["text"],
                    "tokens": result.get("usage", {}).get("total_tokens", 0),
                    "timestamp": asyncio.get_event_loop().time()
                }
            )
        
        return result
    except Exception as e:
        logger.error(f"Error in text generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/", response_model=GenerateResponse)
async def generate_chat(request: ChatRequest):
    """
    Generate chat completions using any supported LLM model
    """
    try:
        logger.info(f"Processing chat request using model: {request.model or 'default'}")
        
        # Optional: Log request to Redis stream
        if redis_manager.is_connected():
            last_message = request.messages[-1].content if request.messages else ""
            request_id = redis_manager.stream_add(
                LLM_REQUESTS_STREAM,
                {
                    "type": "chat",
                    "model": request.model or "default",
                    "message_count": len(request.messages),
                    "last_message_preview": last_message[:100] + "..." if len(last_message) > 100 else last_message,
                    "timestamp": asyncio.get_event_loop().time()
                }
            )
        
        result = controller.chat(
            messages=[{"role": msg.role, "content": msg.content} for msg in request.messages],
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            provider=request.provider,
            additional_params=request.additional_params
        )
        
        # Calculate pricing information
        price_info = controller.calculate_price(
            model=result["model"],
            provider=result["provider"],
            usage=result.get("usage", {})
        )
        result["price"] = price_info
        
        # Optional: Log response to Redis stream
        if redis_manager.is_connected():
            redis_manager.stream_add(
                LLM_RESPONSES_STREAM,
                {
                    "type": "chat",
                    "model": result["model"],
                    "response_preview": result["text"][:100] + "..." if len(result["text"]) > 100 else result["text"],
                    "tokens": result.get("usage", {}).get("total_tokens", 0),
                    "timestamp": asyncio.get_event_loop().time()
                }
            )
        
        return result
    except Exception as e:
        logger.error(f"Error in chat generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models/", response_model=List[ModelInfo])
async def list_models():
    """
    List all available models
    """
    try:
        models = controller.list_models()
        return models
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream/")
async def stream_response(request: ChatRequest):
    """
    Stream responses from supported LLM models
    """
    try:
        logger.info(f"Processing streaming request using model: {request.model or 'default'}")
        
        def generate_stream():
            for chunk in controller.stream(
                messages=[{"role": msg.role, "content": msg.content} for msg in request.messages],
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                provider=request.provider,
                additional_params=request.additional_params
            ):
                yield f"data: {chunk}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"Error in streaming: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-async/")
async def generate_async(request: GenerateRequest, background_tasks: BackgroundTasks):
    """
    Generate text asynchronously
    """
    try:
        task_id = controller.generate_async(
            background_tasks=background_tasks,
            prompt=request.prompt,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            provider=request.provider,
            additional_params=request.additional_params
        )
        
        return {"task_id": task_id, "status": "processing"}
    except Exception as e:
        logger.error(f"Error in async generation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Get the status of an asynchronous task
    """
    try:
        return controller.get_task_status(task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/price/{model}")
async def get_price_info(model: str, input_tokens: int = Query(1000), output_tokens: int = Query(1000)):
    """
    Get pricing information for a specific model
    """
    try:
        price_info = controller.get_model_price(model, input_tokens, output_tokens)
        if not price_info:
            raise HTTPException(status_code=404, detail=f"Price information not available for model {model}")
        
        return price_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting price info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))