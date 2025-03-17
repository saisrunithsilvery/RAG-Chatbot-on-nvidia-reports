from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
import logging
from app.utils.pdf_utils import extract_pdf_content

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class PDFExtractionRequest(BaseModel):
    pdf_path: str
    output_dir: str

@router.post("/extract-pdf/enterprise")
async def extract_pdf(request: PDFExtractionRequest):
    try:
        # Validate paths
        pdf_path = Path(request.pdf_path)
        output_dir = Path(request.output_dir)
        
        # Check if PDF file exists
        if not pdf_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"PDF file not found at path: {pdf_path}"
            )
            
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract PDF content
        zip_path = extract_pdf_content(
            pdf_path=str(pdf_path),
            output_dir=str(output_dir)
        )
        
        return {
            "status": "success",
            "zip_path": zip_path,
            "message": "PDF extraction completed successfully"
        }
        
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDF: {str(e)}"
        )

__all__ = ['router']