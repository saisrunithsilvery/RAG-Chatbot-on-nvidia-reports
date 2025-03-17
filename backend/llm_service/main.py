from fastapi import FastAPI
import logging
import os

from routes import llm_routes
from routes import pdf_routes

# Configure logging with standard library
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

# Set up environment based on configuration
APP_ENV = os.getenv("APP_ENV", "development")
DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")

log.info(f"Starting application in {APP_ENV} mode")

# Create FastAPI instance
app = FastAPI(
    title="PDF Processing with LLM API",
    description="API for processing PDF documents with various LLM providers using LiteLLM",
    version="1.0.0",
    debug=DEBUG
)

# Include routers
app.include_router(llm_routes.router)
app.include_router(pdf_routes.router)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "PDF Processing with LLM API",
        "version": "1.0.0",
        "endpoints": {
            "/llm/generate/": "Generate text using any supported LLM model",
            "/llm/chat/": "Generate chat completions using any supported LLM model",
            "/llm/models/": "List all available models",
            "/llm/stream/": "Stream responses from supported LLM models",
            "/pdf/select_pdfcontent/": "Select previously parsed PDF content",
            "/pdf/upload_pdf/": "Upload and process a new PDF document",
            "/pdf/summarize/": "Generate a summary of PDF content",
            "/pdf/ask_question/": "Ask questions about PDF content",
            "/pdf/extract_keypoints/": "Extract key points from PDF content",
            "/pdf/list_all_pdfs/": "List all available PDF contents"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8002, reload=DEBUG)