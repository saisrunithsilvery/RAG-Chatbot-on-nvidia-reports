# app/main.py
from fastapi import FastAPI
import logging

from app.routes import web_routes
from app.routes import web_handler_routes as web_handler
from app.routes import pdf_routes


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI instance
app = FastAPI(
    title="PDF Processing API",
    description="API for processing PDF documents",
    version="1.0.0"
)

# Include routers
# app.include_router(pdf_routes.router)
app.include_router(web_handler.router)
app.include_router(web_routes.router)
app.include_router(pdf_routes.router)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "PDF Processing API",
        "version": "1.0.0",
         "endpoints": {
        "/web-scraping/opensource/": "Scrape content from website using opensource method",
        "/web-process/opensource": "Process content from website using opensource method",
        "/pdf-process/opensource/": "Process PDF content using opensource method",
          
    }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)