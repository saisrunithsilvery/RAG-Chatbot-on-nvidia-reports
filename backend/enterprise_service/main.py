# app/main.py
from fastapi import FastAPI
import logging
from app.routes.pdf_routes import router as pdf_router
from app.routes.pdf_handler_routes import router as handler_router
from app.routes.web_routes import router as web_routes
from app.routes.web_handler_routes import router as web_handler_routes

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
app.include_router(pdf_router)  # Changed from pdf_routes.router
app.include_router(handler_router)  # Changed from handler_routes.router
app.include_router(web_routes)  # Changed from web_scraping_routes.router
app.include_router(web_handler_routes)  # Changed from web_handler_routes.router

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "PDF Processing API",
        "version": "1.0.0",
        "endpoints": {
            "/extract-pdf/enterprise": "Extract content from PDF file using enterprise method",
            "/process-zip/enterprise": "Process ZIP file using enterprise method",
            "/web-scraping/enterprise": "Scrape content from website using enterprise method",
            "/web-process/": "Process Markdown file with images"
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)