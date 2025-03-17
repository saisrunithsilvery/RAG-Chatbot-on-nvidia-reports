import logging
from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel

from app.utils.web_utils import web_scraping_enterprise as scrape_data

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

@router.post("/web-scraping/enterprise", response_model=WebScrapingResponse)
async def extract_web_data(request: WebScrapingRequest):
    try:
        # Perform web scraping
        md_path = scrape_data(request.url)

        return WebScrapingResponse(
            status="success",
            saved_path=str(md_path),
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