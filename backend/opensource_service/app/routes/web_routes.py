import logging
from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel

from app.utils import web_utils as web_scrape

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI router
router = APIRouter()

class WebScrapingRequest(BaseModel):
    url: str

class WebScrapingResponse(BaseModel):
    status: str
    saved_path: str
    message: str

@router.post("/web-scraping/opensource", response_model=WebScrapingResponse)
async def extract_web_data(request: WebScrapingRequest):
    try:
        # Perform web scraping
        print("request.url", request.url)
        html_path = web_scrape.web_scrape(request.url)  # Changed this line
        print("html_path", html_path)
        return WebScrapingResponse(
            status="success",
            saved_path=str(html_path),
            message="Web scraping completed successfully"
        )

    except Exception as e:
        logger.error(f"Error processing web scraping: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing web scraping: {str(e)}"
        )

# Export router
__all__ = ['router']