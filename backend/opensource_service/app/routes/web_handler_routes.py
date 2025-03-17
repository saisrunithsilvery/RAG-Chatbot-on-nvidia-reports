import logging
import boto3
from botocore.config import Config
from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel
from typing import Optional
from app.utils.web_handler import process_html_with_docling
from urllib.parse import urlparse

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
    error: Optional[str] = None

def generate_presigned_url(bucket_name: str, object_key: str, expiration: int = 3600):
    """Generate a presigned URL for an S3 object"""
    s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))
    try:
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key
            },
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        logger.error(f"Error generating presigned URL: {str(e)}")
        raise

@router.post("/web-process/opensource", response_model=WebScrapingResponse)
async def scrape_web_content(request: WebScrapingRequest):
    """
    Endpoint to handle web scraping requests
    """
    try:
        # Perform web scraping
        markdown_path = process_html_with_docling(request.url)
        logger.info(f"Generated markdown path: {markdown_path}")
        
        try:
            bucket_name = "damg7245-datanexus-pro"
            # Extract bucket name and object key
            base_path = markdown_path.split(f"{bucket_name}.s3.amazonaws.com/")[1]
            
            markdown_key = f"{base_path}markdown/content.md"
            # Clean the base path
            markdown_url = generate_presigned_url(bucket_name, base_path)
            
            
            # Generate presigned URL
            
            
            return WebScrapingResponse(
                status="success",
                saved_path=markdown_url,
                message="Web scraping completed successfully"
            )
        except Exception as e:
            logger.error(f"Error processing S3 path: {str(e)}")
            raise
            
    except Exception as e:
        error_msg = f"Error processing web scraping: {str(e)}"
        logger.error(error_msg)
        return WebScrapingResponse(
            status="error",
            saved_path="",
            message="Web scraping failed",
            error=error_msg
        )

# Export router
__all__ = ['router']