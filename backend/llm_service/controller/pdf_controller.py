import os
import time
import logging
import json
import uuid
import io
from typing import Dict, Any, List, Optional, BinaryIO
from PyPDF2 import PdfReader
import redis
from loguru import logger
import boto3
from botocore.exceptions import ClientError
from datetime import datetime

class PDFController:
    """Controller for PDF document processing"""
    
    def __init__(self):
        """Initialize the PDF controller and Redis connection"""
        # Set up Redis connection
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))
        
        try:
            self.redis = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True  # Auto-decode Redis responses to strings
            )
            # Test connection
            self.redis.ping()
            logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
        except redis.ConnectionError:
            logger.warning(f"Could not connect to Redis at {redis_host}:{redis_port}. Using in-memory storage instead.")
            self.redis = None
        
        # In-memory storage as fallback or for testing
        self.pdf_contents = {}
        
        # Create content directory if it doesn't exist
        self.content_dir = os.getenv("PDF_CONTENT_DIR", "pdf_contents")
        os.makedirs(self.content_dir, exist_ok=True)
            # In-memory storage as fallback or for testing
        # **Storage Configuration**
        self.storage_type = os.getenv("STORAGE_TYPE", "S3")  # Default to S3
        self.s3_bucket_name = os.getenv("S3_BUCKET_NAME", "damg7245-datanexus-pro")

        # **Initialize S3 Client if Using S3**
        if self.storage_type == "S3":
            self.s3_client = boto3.client("s3")
            logger.info(f"Using S3 storage. Bucket: {self.s3_bucket_name}")
        else:
            self.s3_client = None  # Local storage mode
            logger.info(f"Using local storage. Base directory: {self.content_dir}")
    
    def _get_redis_key(self, content_id: str) -> str:
        """Get the Redis key for a PDF content"""
        return f"pdf:content:{content_id}"
    
    def _save_to_redis(self, content_id: str, data: Dict[str, Any]) -> bool:
        """Save PDF content to Redis"""
        if not self.redis:
            return False
        
        try:
            # Convert data to JSON string
            json_data = json.dumps(data)
            # Save to Redis
            self.redis.set(self._get_redis_key(content_id), json_data)
            return True
        except Exception as e:
            logger.error(f"Error saving to Redis: {str(e)}")
            return False
    
    def _load_from_redis(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Load PDF content from Redis"""
        if not self.redis:
            return None
        
        try:
            # Get data from Redis
            json_data = self.redis.get(self._get_redis_key(content_id))
            if not json_data:
                return None
            
            # Parse JSON data
            return json.loads(json_data)
        except Exception as e:
            logger.error(f"Error loading from Redis: {str(e)}")
            return None
    
    def _save_to_file(self, content_id: str, data: Dict[str, Any]) -> bool:
        """Save PDF content to a file"""
        try:
            # Generate filename
            filename = os.path.join(self.content_dir, f"{content_id}.json")
            
            # Save to file
            with open(filename, 'w') as f:
                json.dump(data, f)
            
            return True
        except Exception as e:
            logger.error(f"Error saving to file: {str(e)}")
            return False
    
    def _load_from_file(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Load PDF content from a file"""
        try:
            # Generate filename
            filename = os.path.join(self.content_dir, f"{content_id}.json")
            
            # Check if file exists
            if not os.path.exists(filename):
                return None
            
            # Load from file
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading from file: {str(e)}")
            return None
    
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Extract text from a PDF file
        
        Args:
            pdf_bytes: The PDF file content as bytes
            
        Returns:
            Dict containing extracted text and metadata
        """
        try:
            # Create a PDF reader object
            pdf_stream = io.BytesIO(pdf_bytes)
            pdf_reader = PdfReader(pdf_stream)
            
            # Get number of pages
            num_pages = len(pdf_reader.pages)
            
            # Extract text from each page
            text = ""
            pages = []
            
            for i in range(num_pages):
                page = pdf_reader.pages[i]
                page_text = page.extract_text()
                text += page_text + "\n\n"
                pages.append(page_text)
            
            # Return extracted text and metadata
            return {
                "content": text,
                "pages": pages,
                "page_count": num_pages
            }
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise Exception(f"Error extracting text from PDF: {str(e)}")
    
    def process_pdf(self, content_id: str, filename: str, pdf_bytes: bytes) -> Dict[str, Any]:
        """
        Process a PDF document
        
        Args:
            content_id: Unique ID for the PDF content
            filename: Original filename
            pdf_bytes: The PDF file content as bytes
            
        Returns:
            Dict containing processed PDF content and metadata
        """
        try:
            # Extract text from PDF
            extracted_data = self.extract_text_from_pdf(pdf_bytes)
            
            # Create PDF content object
            pdf_content = {
                "filename": filename,
                "content": extracted_data["content"],
                "pages": extracted_data["pages"],
                "page_count": extracted_data["page_count"],
                "created_at": time.time()
            }
            
            # Save to Redis if available
            redis_success = self._save_to_redis(content_id, pdf_content)
            
            # Also save to file as backup
            file_success = self._save_to_file(content_id, pdf_content)
            
            # Store in memory
            self.pdf_contents[content_id] = pdf_content
            
            logger.info(f"Processed PDF '{filename}' with ID {content_id}: {extracted_data['page_count']} pages")
            
            return pdf_content
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise Exception(f"Error processing PDF: {str(e)}")
    
    async def process_pdf_background(self, content_id: str, filename: str, pdf_bytes: bytes):
        """Background task for processing PDFs"""
        try:
            self.process_pdf(content_id, filename, pdf_bytes)
        except Exception as e:
            logger.error(f"Error in background PDF processing: {str(e)}")
    
    def get_pdf_content(self, content_id: str, folder_path: Optional[str] = None) -> Optional[str]:
        """
        Get PDF content as a string by ID and folder path.

        Args:
            content_id: ID of the PDF content
            folder_path: Path to the folder containing the PDF content

        Returns:
            PDF content as a string, or None if not found
        """
        # Try to get from memory
        if content_id in self.pdf_contents:
            return self.pdf_contents[content_id].get("content")

        # Try to get from Redis
        redis_data = self._load_from_redis(content_id)
        if redis_data:
            # Cache in memory
            self.pdf_contents[content_id] = redis_data
            return redis_data.get("content")

        # If folder_path is provided, try to download file.md
        if folder_path:
            markdown_content = self._download_markdown_file(folder_path)
            
            # If markdown content was found, store it in Redis
            if markdown_content:
                # Prepare data for storage
                data = {
                    "content": markdown_content,
                    "content_type": "markdown",
                    "timestamp": datetime.now().isoformat(),
                }
                
                # Store in Redis
                try:
                    redis_key = f"markdown:{content_id}"
                    self.redis.set(redis_key, json.dumps(data))  # Use self.redis instead of self.redis_client
                    
                    # Cache in memory
                    self.pdf_contents[content_id] = data
                except Exception as e:
                    logger.error(f"Failed to store Markdown content in Redis: {str(e)}")
            
            return markdown_content

        else:
            # Try to get from file without folder path
            file_data = self._load_from_file(content_id)
            if file_data:
                # Cache in memory
                self.pdf_contents[content_id] = file_data
                return file_data.get("content")

        # Not found
        return None
    
    def _download_markdown_file(self, folder_path: str) -> Optional[str]:
        """
        Download the markdown file from the given folder path.
        
        Args:
            folder_path: Path to the folder containing the markdown file
                
        Returns:
            Markdown content as a string, or None if not found.
        """
        try:
            
            # Ensure `storage_type` is defined
            if not hasattr(self, "storage_type"):
                raise AttributeError("storage_type is not set in PDFController.")

            if self.storage_type.upper() == 'S3':
                if not self.s3_client or not self.s3_bucket_name:
                    raise ValueError("S3 client or bucket name not initialized.")
                
                bucket_name = self.s3_bucket_name
                s3_key = f"{folder_path}markdown/content.md".lstrip("/")  # Ensure no leading slash
                
                try:
                    response = self.s3_client.get_object(Bucket=bucket_name, Key=s3_key)
                    markdown_content = response["Body"].read().decode("utf-8")
             
                    return markdown_content
                except self.s3_client.exceptions.NoSuchKey:
                    logger.error(f"Markdown file not found in S3: {s3_key}")
                    return None
                except Exception as e:
                    logger.error(f"Error downloading from S3: {e}")
                    return None

            # Handle local storage
            file_path = os.path.join(self.base_dir, folder_path, "file.md")
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    return f.read()
            else:
                logger.error(f"Markdown file not found locally: {file_path}")

        except Exception as e:
            logger.error(f"Error downloading markdown file from {folder_path}: {str(e)}")
        
        return None
    def list_all_pdfs(self) -> Dict[str, Dict[str, Any]]:
        """
        List all available PDF contents from S3 bucket
        
        Returns:
            Dict mapping content IDs to PDF content metadata
        """
       
        
        # Initialize dictionary to store contents
        contents = {}
        
        try:
            # Initialize S3 client
            s3_client = boto3.client('s3')
            
            # Define bucket name and prefix
            bucket_name = 'damg7245-datanexus-pro'
            prefix = 'pdf-extract/'
            
            # List all folders in the pdf-extract directory
            response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
                Delimiter='/'
            )
            
            # Extract folders from the response
            if 'CommonPrefixes' in response:
                for obj in response['CommonPrefixes']:
                    folder_path = obj['Prefix']
                    folder_name = folder_path.rstrip('/').split('/')[-1]
                    
                    # Extract content ID from folder name
                    # Format: PDF_Extract_[DATE]_[TIME]_[ID]
                    content_id = folder_name.split('_')[-1]
                    
                    # Check if folder contains markdown/content.md
                    try:
                        s3_client.head_object(
                            Bucket=bucket_name,
                            Key=f"{folder_path}markdown/content.md"
                        )
                        has_markdown = True
                    except ClientError:
                        has_markdown = False
                    
                    # Get folder creation time (by checking the folder itself)
                    try:
                        folder_info = s3_client.list_objects_v2(
                            Bucket=bucket_name,
                            Prefix=folder_path,
                            MaxKeys=1
                        )
                        if 'Contents' in folder_info and folder_info['Contents']:
                            last_modified = folder_info['Contents'][0]['LastModified']
                        else:
                            last_modified = None
                    except ClientError:
                        last_modified = None
                    
                    # Store folder metadata
                    contents[content_id] = {
                        'folder_name': folder_name,
                        'folder_path': folder_path,
                        'has_markdown': has_markdown,
                        'last_modified': last_modified,
                        'source': 's3'
                    }
                    
        except Exception as e:
            logger.error(f"Error listing S3 PDF contents: {str(e)}")
        
        return contents