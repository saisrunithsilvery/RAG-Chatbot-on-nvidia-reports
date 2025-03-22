from fastapi import APIRouter, Depends, File, Form, UploadFile, Request, status, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
from pydantic import BaseModel
import json
from controllers.s3_pdf_controller import S3ProcessRequest, FileController

# Create router
router = APIRouter()

# Response models
class UploadResponse(BaseModel):
    filename: str
    file_url: str
    file_size: int
    content_type: str
    upload_date: str

class ProcessingRequest(BaseModel):
    method: str
    file: str
    parsetype: Optional[str] = None
    chunking_strategy: Optional[str] = None
    vectordb: Optional[str] = None

async def trigger_airflow_dag(markdown_url: str, chunking_strategy: str, vectordb: str):
    """
    Trigger the Airflow DAG for document chunking after receiving the markdown URL
    """
    try:
        from urllib.parse import urlparse
        import uuid
        import os
        import httpx
        
        parsed_url = urlparse(markdown_url)
        path_parts = parsed_url.path.lstrip('/').split('/')
        s3_bucket = parsed_url.netloc.split('.')[0]  # Extract bucket name
        s3_key = '/'.join(path_parts)  # S3 key
        
        collection_name = f"collection_{uuid.uuid4().hex[:12]}"
        
        payload = {
            "conf": {
                "s3_bucket": s3_bucket,
                "s3_key": s3_key,
                "chunking_strategy": chunking_strategy,
                "vectordb": vectordb,
                "collection_name": collection_name
            }
        }
        
        airflow_api_endpoint = os.getenv(
            "AIRFLOW_API_ENDPOINT", "http://67.205.150.201/:8080/api/v1/dags/document_chunking_pipeline/dagRuns"
        )
        
        airflow_username = os.getenv("AIRFLOW_USERNAME", "airflow")
        airflow_password = os.getenv("AIRFLOW_PASSWORD", "airflow")
        auth = None
        if airflow_username and airflow_password:
            from httpx import BasicAuth
            auth = BasicAuth(airflow_username, airflow_password)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                airflow_api_endpoint,
                json=payload,
                auth=auth,
                timeout=30.0
            )
            
            if response.status_code not in [200, 201]:
                return {"status": "error", "message": f"Failed to trigger Airflow DAG: {response.text}"}
            
            return {
                "status": "success",
                "airflow_response": response.json(),
                "collection_name": collection_name
            }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"Error triggering Airflow DAG: {str(e)}"}

@router.post("/process-s3", status_code=status.HTTP_200_OK)
async def process_s3_pdf(request_data: S3ProcessRequest):
    """
    Process a PDF file directly from an S3 URL without uploading
    
    Request body should include:
    - method: "s3"
    - s3_url: The S3 URL of the PDF to process
    - parsetype: Parser type (docling, mistral_ai, enterprise, opensource)
    - chunking_strategy: Optional, defaults to "recursive"
    - vectordb: Optional, defaults to "faiss"
    """
    controller = FileController()
    try:
        # Validate method is "s3"
        if request_data.method != "s3":
            return JSONResponse(
                status_code=400, 
                content={"status": "error", "message": "Only 's3' method is supported for this endpoint"}
            )
        
        # Process the file using the direct S3 method
        parsing_result = await controller.process_s3_directly(request_data)
        
        # If successful and markdown_url is available, trigger the Airflow DAG
        if parsing_result.get("status") == "success" and "markdown_url" in parsing_result:
            markdown_url = parsing_result["markdown_url"]
            chunking_strategy = request_data.chunking_strategy or "recursive"
            vectordb = request_data.vectordb or "faiss"
            
            dag_result = await trigger_airflow_dag(markdown_url, chunking_strategy, vectordb)
            
            # Make sure collection_name is included in the main response
            collection_name = dag_result.get("collection_name", "")
            
            return {
                "status": "success",
                "markdown_url": markdown_url,
                "collection_name": collection_name,  # Explicitly include collection_name at the top level
                "airflow_status": dag_result
            }
            
        return {"status": "success", "parsing_result": parsing_result}
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500, 
            content={"status": "error", "message": f"Error processing S3 PDF: {str(e)}"}
        )