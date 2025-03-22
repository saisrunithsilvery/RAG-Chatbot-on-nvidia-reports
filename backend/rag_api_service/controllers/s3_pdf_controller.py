import boto3
import os
import httpx
import json
from dotenv import load_dotenv
from typing import Optional, Dict, Any
import uuid
from datetime import datetime
from fastapi import UploadFile, HTTPException, status
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# AWS S3 configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Parser service endpoints
DOCLING_ENDPOINT = os.getenv("DOCLING_ENDPOINT", "http://localhost:8003/docling_process_s3_pdf/")
MISTRAL_AI_ENDPOINT = os.getenv("MISTRAL_AI_ENDPOINT", "http://localhost:8004/ocr/extract-pdf/mistral_ai/")
ENTERPRISE_ENDPOINT = os.getenv("ENTERPRISE_ENDPOINT", "http://localhost:8001/extract-pdf/enterprise")
OPENSOURCE_ENDPOINT = os.getenv("OPENSOURCE_ENDPOINT", "http://localhost:8002/pdf-process/opensource")

# Pydantic model for direct S3 processing request
class S3ProcessRequest(BaseModel):
    method: str  # Should be "s3"
    s3_url: str
    parsetype: str
    chunking_strategy: Optional[str] = None
    vectordb: Optional[str] = None

class FileController:
    def __init__(self):
        # Validate environment variables
        if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME]):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="S3 configuration is missing. Please set the required environment variables."
            )
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
    
    async def upload_file(self, file: UploadFile, folder: Optional[str]):
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Invalid file"
            )
        
        try:
            # Generate a unique filename
            sanitized_filename = os.path.basename(file.filename)
            # Set the S3 path
            s3_path = f"{folder}/{sanitized_filename}" if folder else sanitized_filename
            
            # Read file content
            contents = await file.read()
            file_size = len(contents)
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=AWS_BUCKET_NAME,
                Key=s3_path,
                Body=contents,
                ContentType=file.content_type
            )
            
            # Generate URL to the file
            file_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_path}"
            
            # Return success response
            return {
                "filename": sanitized_filename,
                "file_url": file_url,
                "file_size": file_size,
                "content_type": file.content_type,
                "upload_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            # Log the error
            print(f"Error uploading file: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Failed to upload file: {str(e)}"
            )
    
    async def process_file(self, file_url: str, parse_type: str, chunking_strategy: Optional[str] = None, vectordb: Optional[str] = None):
        """
        Process a file that has been uploaded to S3 using one of the parser services
        
        Args:
            file_url: The S3 URL of the uploaded file
            parse_type: Type of parsing to perform (docling, mistral_ai, enterprise, opensource)
            chunking_strategy: Optional chunking strategy
            vectordb: Optional vector database type
            
        Returns:
            Parser service response
        """
        # Get parser endpoints from environment variables
        PARSER_ENDPOINTS = {
            "docling": os.getenv("DOCLING_ENDPOINT", "http://localhost:8003/docling_process_s3_pdf/"),
            "mistral_ai": os.getenv("MISTRAL_AI_ENDPOINT", "http://localhost:8004/ocr/extract-pdf/mistral_ai/"),
            "enterprise": os.getenv("ENTERPRISE_ENDPOINT", "http://localhost:8001/extract-pdf/enterprise"),
            "opensource": os.getenv("OPENSOURCE_ENDPOINT", "http://localhost:8002/pdf-process/opensource")
        }
        
        if parse_type not in PARSER_ENDPOINTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported parser type: {parse_type}"
            )
        
        endpoint = PARSER_ENDPOINTS[parse_type]
        
        # Create payload with S3 URL and optional parameters
        payload = {
            "s3_url": file_url
        }
        
        # Add optional parameters if provided
        if chunking_strategy:
            payload["chunking_strategy"] = chunking_strategy
            
        if vectordb:
            payload["vectordb"] = vectordb
        
        # Create async HTTP client with appropriate timeout
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                # Log the request attempt
                print(f"Sending request to parser service at {endpoint}")
                print(f"Payload: {json.dumps(payload)}")
                
                # Make the request with explicit timeout and follow redirects
                response = await client.post(
                    endpoint,
                    json=payload,
                    timeout=120.0,  # Explicit request timeout
                    follow_redirects=True  # Handle any redirects
                )
                
                # Log the raw response for debugging
                print(f"Received response with status code: {response.status_code}")
                
                if response.status_code != 200:
                    error_msg = f"Parser service returned error: {response.text}"
                    print(error_msg)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=error_msg
                    )
                
                # Parse the response
                parsing_result = response.json()
                print(f"Received response from parser service: {json.dumps(parsing_result)}")
                
                # Check if the response contains the expected fields
                if "status" not in parsing_result or parsing_result["status"] != "success":
                    error_msg = f"Parser service returned unexpected response format: {parsing_result}"
                    print(error_msg)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=error_msg
                    )
                
                # Return the parser service response 
                return parsing_result
                
            except httpx.RequestError as e:
                error_msg = f"Error connecting to parser service: {str(e)}"
                print(error_msg)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_msg
                )
            
    async def process_s3_directly(self, request_data: S3ProcessRequest):
        """
        Process a file directly from S3 URL without requiring upload
        
        Args:
            request_data: The S3ProcessRequest object containing s3_url, parsetype, etc.
            
        Returns:
            Parser service response
        """
        # Validate the request method
        if request_data.method != "s3":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported method: {request_data.method}. Only 's3' method is supported."
            )
            
        # Process the file using the existing process_file method
        # Pass all parameters to the parser service
        return await self.process_file(
            file_url=request_data.s3_url, 
            parse_type=request_data.parsetype,
            chunking_strategy=request_data.chunking_strategy,
            vectordb=request_data.vectordb
        )
            
    async def list_files(self, folder: Optional[str]):
        try:
            prefix = f"{folder}/" if folder else ""
            
            response = self.s3_client.list_objects_v2(
                Bucket=AWS_BUCKET_NAME,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                for item in response['Contents']:
                    file_key = item['Key']
                    file_name = os.path.basename(file_key)
                    file_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_key}"
                    
                    files.append({
                        "filename": file_name,
                        "file_url": file_url,
                        "size": item['Size'],
                        "last_modified": item['LastModified'].isoformat()
                    })
                    
            return {"files": files}
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"Failed to list files: {str(e)}"
            )