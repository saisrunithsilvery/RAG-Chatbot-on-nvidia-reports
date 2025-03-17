from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import logging
import boto3
from botocore.config import Config
from app.utils.pdf_handler import process_zip

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class ZIPProcessRequest(BaseModel):
    zip_path: str

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

@router.post("/process-zip/enterprise")
async def process_zip_file(request: ZIPProcessRequest):
    try:
        # Validate ZIP file path
       
        zip_path = Path(request.zip_path)
        if not zip_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"ZIP file not found at path: {zip_path}"
            )
        
        if not zip_path.suffix.lower() == '.zip':
            raise HTTPException(
                status_code=400,
                detail="File must be a ZIP archive"
            )
        
        # Process the ZIP file and get the S3 base path
        base_url = process_zip(zip_path=str(zip_path))
       
        
        # Extract bucket name and key prefix from the base_url
        # Convert https://bucket.s3.amazonaws.com/path to bucket and path
        bucket_name = "damg7245-datanexus-pro"
        base_path = base_url.split(f"{bucket_name}.s3.amazonaws.com/")[1]
        
        # Generate presigned URLs
        markdown_key = f"{base_path}markdown/content.md"
        images_key = f"{base_path}images"
        
        markdown_url = generate_presigned_url(bucket_name, markdown_key)
        
        return {
            "status": "success",
            "message": "ZIP file processed successfully",
            "output_locations": {
                "markdown_file": markdown_url,
                "base_path": base_path,
                "bucket": bucket_name
            }
        }
        
    except Exception as e:
        logger.error(f"Error processing ZIP file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing ZIP file: {str(e)}"
        )

__all__ = ['router']