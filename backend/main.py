from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import uvicorn
from app.routers import handler_routes, file_storage, pdf_extract_routes, web_scraping_routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Document Analysis API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(handler_routes.router, prefix="/api", tags=["LLM Processing"])
app.include_router(pdf_extract_routes.router, prefix="/api", tags=["PDF Processing"])
app.include_router(file_storage.router, prefix="/api", tags=["File Storage"])
app.include_router(web_scraping_routes.router, prefix="/api", tags=["Web Scraping"])

@app.get("/")
async def root():
    return {"message": "Document Analysis API is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)