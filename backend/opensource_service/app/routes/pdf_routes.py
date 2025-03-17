import logging
import boto3
import tempfile
from botocore.config import Config
from fastapi import FastAPI, HTTPException, APIRouter, UploadFile, File
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.utils.pdf_utils import PdfConverter
from urllib.parse import urlparse
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI router
router = APIRouter()

class PdfProcessingResponse(BaseModel):
    status: str
    markdown_url: str
    s3_base_path: Optional[str] = None
    images: Optional[List[Dict[str, str]]] = None
    table_count: Optional[int] = None
    image_count: Optional[int] = None
    message: str
    error: Optional[str] = None

def generate_presigned_url(bucket_name: str, object_key: str, expiration: int = 3600) -> str:
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

def extract_s3_path_components(s3_url: str) -> tuple[str, str]:
    """Extract bucket name and object key from S3 URL"""
    parsed = urlparse(s3_url)
    bucket_name = parsed.netloc.split('.')[0]
    object_key = parsed.path.lstrip('/')
    return bucket_name, object_key

@router.post("/pdf-process/opensource", response_model=PdfProcessingResponse)
async def process_pdf_content(file: UploadFile = File(...)) -> PdfProcessingResponse:
    """
    Endpoint to handle PDF processing requests
    
    Args:
        file: Uploaded PDF file
        
    Returns:
        PdfProcessingResponse: Processing results
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be a PDF"
        )

    pdf_path = None
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            pdf_path = Path(tmp_file.name)
        
        # Initialize PDF converter
        pdf_converter = PdfConverter()
        
        # Process the PDF
        result = pdf_converter.process_pdf(pdf_path)
        
        if result['status'] != 'success':
            return PdfProcessingResponse(
                status="error",
                markdown_url="",
                message="PDF processing failed",
                error=result.get('message', 'Unknown error occurred')
            )
        
        try:
            # Generate presigned URL for the markdown file
            bucket_name, markdown_key = extract_s3_path_components(result['markdown_s3_url'])
            markdown_url = generate_presigned_url(bucket_name, markdown_key)
            
            # Generate presigned URLs for images
            if result.get('images'):
                for image in result['images']:
                    _, image_key = extract_s3_path_components(image['s3_url'])
                    image['s3_url'] = generate_presigned_url(bucket_name, image_key)
            
            return PdfProcessingResponse(
                status="success",
                markdown_url=markdown_url,
                s3_base_path=result['s3_base_path'],
                images=result.get('images'),
                table_count=result.get('table_count'),
                image_count=result.get('image_count'),
                message="PDF processing completed successfully"
            )
            
        except Exception as e:
            logger.error(f"Error processing S3 paths: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error generating presigned URLs: {str(e)}"
            )
            
    except Exception as e:
        error_msg = f"Error processing PDF: {str(e)}"
        logger.error(error_msg)
        return PdfProcessingResponse(
            status="error",
            markdown_url="",
            message="PDF processing failed",
            error=error_msg
        )
    
    finally:
        # Clean up temporary file
        if pdf_path:
            try:
                pdf_path.unlink(missing_ok=True)
            except Exception as e:
                logger.error(f"Error cleaning up temporary file: {str(e)}")

# Export router
__all__ = ['router']