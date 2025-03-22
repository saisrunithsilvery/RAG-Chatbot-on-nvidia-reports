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
            # file_extension = os.path.splitext(file.filename)[1]
            # unique_filename = f"{uuid.uuid4()}{file_extension}"
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
        
        # Create payload with just the S3 URL as required
        payload = {
            "s3_url": file_url
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                # Send request to parser service
                print(f"Sending request to parser service at {endpoint}")
                print(f"Payload: {json.dumps(payload)}")
                
                response = await client.post(
                    endpoint,
                    json=payload,
                    timeout=180.0,  # Even longer timeout
                    headers={"Content-Type": "application/json"},
                    follow_redirects=True
                )
                
                # Check if response is valid
                if response.status_code != 200:
                    error_text = response.text if response.text else "Empty response received"
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Parser service returned error: {error_text}"
                    )
                
                # Parse the response with error handling
                try:
                    parsing_result = response.json()
                except json.JSONDecodeError:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Parser service returned invalid JSON response"
                    )
                    
                print(f"Received response from parser service: {json.dumps(parsing_result)}")
                
                # Check if the response contains the expected fields
                if not parsing_result:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Parser service returned empty response"
                    )
                    
                if "status" not in parsing_result:
                    # Fake a status for malformed responses that might still be useful
                    parsing_result["status"] = "success"
                    
                # Return the parser service response 
                return parsing_result
                
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error connecting to parser service: {str(e)}"
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