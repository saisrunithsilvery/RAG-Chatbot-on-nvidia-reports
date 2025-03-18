import os
import uuid
import json
import time
from datetime import datetime
from typing import Optional, Dict, List
from fastapi import UploadFile, BackgroundTasks, HTTPException,Request
import aiofiles
import httpx
import re
import config
from utils.mistral_ocr import process_file_with_mistral_ocr
from utils.s3_upload import upload_file_to_s3, upload_text_to_s3

# Simple in-memory storage for job status (replace with a database in production)
job_store = {}

async def process_document(
    file: UploadFile,
    document_id: Optional[str] = None,
    callback_url: Optional[str] = None,
    file_path: Optional[str] = None
    
) -> str:
    """
    Process a document with Mistral OCR and upload it to S3
    
    Args:
        file: The uploaded file
        background_tasks: FastAPI background tasks
        document_id: Optional custom ID for the document
        callback_url: Optional URL to call when processing is complete
        
    Returns:
        The job ID
    """
    # Validate file
    if not file.filename:
        raise HTTPException(400, "File must have a filename")
    
    # Generate a job ID and document ID if not provided
    job_id = str(uuid.uuid4())
    unique_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    process_folder = f"PDF_Extract_{timestamp}_{unique_id}"
    print("process_folder:", process_folder)
    if not document_id:
        document_id = process_folder
    
    # Create a temporary file to store the upload
   # file_path = os.path.join(config.TEMP_UPLOAD_DIR, f"{job_id}_{file.filename}")
    
    
    # Initialize job status
    
    job_store[job_id] = {
        "job_id": job_id,
        "document_id": document_id,
        "filename": file.filename,
        "status": "processing",
        "created_at": time.time(),
        "updated_at": time.time(),
        "file_path": file_path,
        "callback_url": callback_url,
        "s3_url": None,
        "ocr_result_url": None,
        "error": None
    }
    
    #Add the processing task to background tasks
    await _process_document_background(
        job_id=job_id,
        file_path=file_path,
        original_filename=file.filename,
        document_id=document_id,
        callback_url=callback_url
    )
    
    return job_id

async def _process_document_background(
    job_id: str,
    file_path: str,
    original_filename: str,
    document_id: str,
    callback_url: Optional[str] = None
) -> None:
    """
    Background task to process a document with Mistral OCR and upload to S3
    """
    try:
        # Define S3 paths based on the process folder
        base_s3_path = f"pdf-extract/{document_id}"
        
        # Upload original file to S3
        s3_key = f"{base_s3_path}/original/{original_filename}"
        s3_url = await upload_file_to_s3(file_path, s3_key)
        
        # Update job status
        job_store[job_id]["s3_url"] = s3_url
        job_store[job_id]["status"] = "ocr_processing"
        job_store[job_id]["updated_at"] = time.time()
        
        # Get the correct S3 URL for the uploaded file
        s3_pdf_url = f"https://damg7245-datanexus-pro.s3.us-east-1.amazonaws.com/{s3_key}"

        # Process with Mistral OCR
        ocr_result = await process_file_with_mistral_ocr(s3_pdf_url)
        
        # Upload OCR result to S3
        markdown_s3_path = f"{base_s3_path}/ocr_pdf"
        ocr_result_key = f"{markdown_s3_path}/result.json"
        ocr_result_url = await upload_text_to_s3(
            json.dumps(ocr_result, indent=2),
            ocr_result_key
        )
        
        # Update job status to completed
        job_store[job_id]["status"] = "completed"
        job_store[job_id]["ocr_result_url"] = ocr_result_url
        # Create a more robust OCR data summary
        ocr_data = {
            "text_length": len(ocr_result.get("text", "")),
            "pages_count": len(ocr_result.get("pages", [])),
        }
        
        # Add additional debug information if available
        if "raw_response" in ocr_result:
            ocr_data["raw_response_available"] = True
            
        # Store the OCR data
        job_store[job_id]["ocr_data"] = ocr_data
        job_store[job_id]["updated_at"] = time.time()
        
        # Clean up the temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # Call the callback URL if provided
        if callback_url:
            await _call_callback(callback_url, {
                "job_id": job_id,
                "status": "completed",
                "document_id": document_id,
                "s3_url": s3_url,
                "ocr_result_url": ocr_result_url
            })
            
    except Exception as e:
        # Update job status to failed
        job_store[job_id]["status"] = "failed"
        job_store[job_id]["error"] = str(e)
        job_store[job_id]["updated_at"] = time.time()
        
        # Clean up the temporary file if it exists
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # Call the callback URL with error if provided
        if callback_url:
            await _call_callback(callback_url, {
                "job_id": job_id,
                "status": "failed",
                "document_id": document_id,
                "error": str(e)
            })

async def _call_callback(url: str, data: Dict) -> None:
    """Call a callback URL with the given data"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=data, timeout=10.0)
    except Exception as e:
        # Log the callback error but don't fail the overall process
        print(f"Callback error: {str(e)}")

async def get_document_status(job_id: str) -> Dict:
    """Get the status of a document processing job"""
    if job_id not in job_store:
        raise HTTPException(404, f"Job ID {job_id} not found")
        
    # Return a copy of the job data without internal details
    job_data = dict(job_store[job_id])
    
    # Remove internal fields
    if "file_path" in job_data:
        del job_data["file_path"]
        
    return job_data

async def get_processing_history(limit: int = 10, skip: int = 0) -> List[Dict]:
    """Get a list of processing jobs"""
    # Sort jobs by creation time (newest first)
    sorted_jobs = sorted(
        job_store.values(),
        key=lambda x: x.get("created_at", 0),
        reverse=True
    )
    
    # Apply pagination
    paginated_jobs = sorted_jobs[skip:skip + limit]
    
    # Remove internal fields
    result = []
    for job in paginated_jobs:
        job_copy = dict(job)
        if "file_path" in job_copy:
            del job_copy["file_path"]
        result.append(job_copy)
        
    return result