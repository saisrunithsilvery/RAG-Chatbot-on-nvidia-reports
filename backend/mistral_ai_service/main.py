import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import config
from routes.ocr_routes import router as ocr_router

# Initialize FastAPI application
app = FastAPI(
    title=config.API_TITLE,
    description=config.API_DESCRIPTION,
    version=config.API_VERSION,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify in production to specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.max_request_size = 100 * 1024 * 1024  # 100 MB limit

# Register routers
app.include_router(ocr_router, prefix="/api/v1")

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Document OCR API Service",
        "version": config.API_VERSION,
        "docs_url": "/docs",
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)