from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import logging
from controller.ocr_controller import process_document
from typing import Dict

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ocr",
    tags=["OCR"],
    responses={404: {"description": "Not found"}},
)

class DocumentRequest(BaseModel):
    s3_url: str

class DocumentResponse(BaseModel):
    status: str
    markdown_url: str

@router.post("/extract-pdf/mistral_ai", response_model=DocumentResponse)
async def process_pdf_document(request: DocumentRequest):
    """
    Process a PDF document from an S3 URL and convert it to markdown
    
    Parameters:
    - s3_url: URL of the PDF document in S3
    
    Returns:
    - status: Processing status
    - markdown_url: URL of the generated markdown file
    """
    try:
        logger.info(f"Received request to process document: {request.s3_url}")
        result = await process_document(request.s3_url)
        logger.info(f"Document processed successfully: {result['markdown_url']}")
        return result
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))