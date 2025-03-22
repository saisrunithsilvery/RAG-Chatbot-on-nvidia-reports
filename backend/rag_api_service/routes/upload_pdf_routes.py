from fastapi import APIRouter, Depends, File, Form, UploadFile, Request, status, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
from pydantic import BaseModel
import json
from controllers.upload_pdf_controller import FileController

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
            "AIRFLOW_API_ENDPOINT", "http://67.205.150.201:8080/api/v1/dags/document_chunking_pipeline/dagRuns"
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

# @router.post("/upload/simple", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
# async def upload_file_simple(
#     file: UploadFile = File(...),
#     folder: Optional[str] = "raw_reports"
# ):
#     controller = FileController()
#     return await controller.upload_file(file, folder)

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_and_process(
    file: UploadFile = File(...),
    request_data: str = Form(None)
):
    print(request_data)
    controller = FileController()
    try:
        # Initialize defaults before attempting to parse request_data
        method = "upload"
        folder = "raw_reports"
        parse_type = None
        chunking_strategy = "recursive"
        vectordb = "faiss"
        
        # Only try to parse and extract values from request_data if it exists
        if request_data:
            try:
                body_data = json.loads(request_data)
                if body_data:
                    method = body_data.get("method", method)
                    parse_type = body_data.get("parsetype", parse_type)
                    chunking_strategy = body_data.get("chunking_strategy", chunking_strategy)
                    vectordb = body_data.get("vectordb", vectordb)
            except json.JSONDecodeError:
                return JSONResponse(
                    status_code=400, 
                    content={"status": "error", "message": "Invalid JSON in request_data"}
                )
        
        if method != "upload":
            return JSONResponse(
                status_code=400, 
                content={"status": "error", "message": "Only 'upload' method is supported"}
            )
        
        upload_result = await controller.upload_file(file, folder)
        
        if parse_type:
            parsing_result = await controller.process_file(
                file_url=upload_result["file_url"],
                parse_type=parse_type,
                chunking_strategy=chunking_strategy,
                vectordb=vectordb
            )
            
            if parsing_result.get("status") == "success" and "markdown_url" in parsing_result:
                markdown_url = parsing_result["markdown_url"]
                try:
                    dag_result = await trigger_airflow_dag(markdown_url, chunking_strategy, vectordb)
                    
                    # Extract collection_name from the DAG result
                    collection_name = dag_result.get("collection_name", "")
                    
                    return {
                        "status": "success",
                        "markdown_url": markdown_url,
                        "collection_name": collection_name,  # Explicitly include collection_name at the top level
                        "airflow_status": dag_result
                    }
                except Exception as e:
                    # Return success with markdown but error with Airflow
                    return {
                        "status": "success",
                        "markdown_url": markdown_url,
                        "airflow_status": {
                            "status": "error",
                            "message": f"Error triggering Airflow DAG: {str(e)}"
                        }
                    }
            return {"status": "success", "upload_info": upload_result, "parsing_result": parsing_result}
        
        return {"status": "success", "upload_info": upload_result}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/files", status_code=status.HTTP_200_OK)
async def list_files(folder: Optional[str] = "raw_reports"):
    controller = FileController()
    return await controller.list_files(folder)

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return JSONResponse(content={"status": "ok"})