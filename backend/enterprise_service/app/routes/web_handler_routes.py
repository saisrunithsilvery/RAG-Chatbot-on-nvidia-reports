import logging
from pathlib import Path
from fastapi import HTTPException, APIRouter
from pydantic import BaseModel
import boto3
from app.utils.web_handler import download_and_replace_images
from botocore.config import Config
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI router
router = APIRouter()

class WebScrapingRequest(BaseModel):
    md_path: str

class WebScrapingResponse(BaseModel):
    status: str
    saved_path: str
    message: str
    
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
    
@router.post("/web-process/", response_model=WebScrapingResponse)
async def extract_web_data(request: WebScrapingRequest):
    try:
        # Use the md_path from the request instead of creating a new one
       
        markdown_path = download_and_replace_images(request.md_path)
        
       
        bucket_name = "damg7245-datanexus-pro"
        base_path = markdown_path.split(f"{bucket_name}.s3.amazonaws.com/")[1]
        
        # Generate presigned URLs
        markdown_key = f"{base_path}markdown/content.md"
       
        markdown_url = generate_presigned_url(bucket_name, markdown_key)
           
      
        return WebScrapingResponse(
            status="success",
            saved_path=str(markdown_url),
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