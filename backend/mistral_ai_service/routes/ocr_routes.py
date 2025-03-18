from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Form, status,Request
from fastapi.responses import JSONResponse
from typing import Optional
import os
import config
from controller.ocr_controller import process_document, get_document_status, get_processing_history
from starlette.formparsers import MultiPartParser # type: ignore
from datetime import datetime
import uuid
MultiPartParser.max_part_size = 10 * 1024 * 1024  # 10MB
MultiPartParser.max_file_size = 20 * 1024 * 1024   # 20MB
router = APIRouter(
    prefix="/ocr",
    tags=["OCR Operations"],
    responses={404: {"description": "Not found"}},
)

if not os.path.exists(config.TEMP_UPLOAD_DIR):
    os.makedirs(config.TEMP_UPLOAD_DIR)
@router.post("/process/", status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    document_id: Optional[str] = None,
    callback_url: Optional[str] = None,
):
    """
    Upload a large file (up to 100MB).
    
    - **file**: The file to upload
    - **description**: Optional description of the file
    """
    # Generate a unique filename to prevent overwrites
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
        
    unique_id = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(config.TEMP_UPLOAD_DIR, f"{unique_id}_{file.filename}")
    # Check file size before saving (100MB limit)
    # We read in chunks to avoid loading the entire file into memory
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    
    try:
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                file_size += len(chunk)
                
                # Check if file size exceeds the limit (100MB)
                if file_size > 100 * 1024 * 1024:  # 100MB in bytes
                    # Close and remove the partial file
                    buffer.close()
                    os.remove(file_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File too large. Maximum size is 100MB."
                    )
                
                buffer.write(chunk)
        job_id = await process_document(
            file=file,
            document_id=document_id,
            callback_url=callback_url,
            file_path=file_path
        )
                
        # File upload completed successfully
        return {
            "message": "Document processing started",
            "job_id": job_id,
            "status": "processing",
            "status_url": f"/api/v1/ocr/status/{job_id}"
        }
        
    except Exception as e:
        # Handle any other exceptions
        if os.path.exists(file_path):
            os.remove(file_path)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during file upload: {str(e)}"
        )

@router.get("/status/{job_id}")
async def check_job_status(job_id: str):
    """
    Check the status of a document processing job
    
    - **job_id**: The ID of the job to check
    """
    try:
        status_data = await get_document_status(job_id)
        return status_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {str(e)}"
        )

@router.get("/history")
async def get_processing_jobs_history(limit: int = 10, skip: int = 0):
    """
    Get history of document processing jobs
    
    - **limit**: Maximum number of records to return
    - **skip**: Number of records to skip (for pagination)
    """
    try:
        history = await get_processing_history(limit=limit, skip=skip)
        return {"history": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving history: {str(e)}"
        )