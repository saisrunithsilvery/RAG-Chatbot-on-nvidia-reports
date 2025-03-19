from fastapi import FastAPI, HTTPException, APIRouter, UploadFile, File
from pydantic import BaseModel
from pathlib import Path
import logging

from docling_converter import DoclingConverter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class PDFExtractionRequest(BaseModel):
    pdf_path: str
    output_dir: str

@router.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    logger.info(f"Received file: {file.filename}")

    # Validate file extension
    if not file.filename.lower().endswith(".pdf"):
        logger.error("Invalid file type uploaded.")
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    # Define output directory
    output_dir = Path("./data/parsed")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save the uploaded file
    file_path = output_dir / file.filename
    try:
        with open(file_path, "wb") as f:
            f.write(await file.read())
        logger.info(f"File saved successfully: {file_path}")
    except Exception as e:
        logger.error(f"Failed to save the file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save the file: {str(e)}")
    
    # Process the PDF
    try:
        converter = DoclingConverter()
        result = converter.process_pdf(file_path, output_dir)
        
        # Validate extracted content
        if not result or (isinstance(result, list) and not any(res.get("content") for res in result)):
            logger.warning(f"No valid content extracted from: {file.filename}")
            raise HTTPException(status_code=422, detail="The uploaded PDF is empty or not readable.")

        logger.info(f"PDF processing completed: {file.filename}")
    except Exception as e:
        logger.error(f"Failed to process the PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process the PDF: {str(e)}")
    
    return {"filename": file.filename, "status": "success", "result": result}