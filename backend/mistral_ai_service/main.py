from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
import logging

from routes.ocr_routes import router as ocr_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Mistral OCR API",
    description="API for converting PDF documents to markdown using Mistral OCR",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(ocr_router, prefix="/api/v1")

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to Mistral OCR API", "status": "online"}

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    logger.info("Starting Mistral OCR API server")
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)