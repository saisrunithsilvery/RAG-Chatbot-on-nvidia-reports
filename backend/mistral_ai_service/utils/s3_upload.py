import os
import asyncio
import mimetypes
import boto3
from botocore.exceptions import ClientError
from typing import Optional

import config

async def upload_file_to_s3(file_path: str, s3_key: str, content_type: Optional[str] = None) -> str:
    """
    Upload a file to S3
    
    Args:
        file_path: Local path to the file
        s3_key: S3 object key (path within the bucket)
        content_type: Optional content type, will be guessed if not provided
        
    Returns:
        S3 URL of the uploaded file
    """
    # Validate inputs
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    if not config.S3_BUCKET_NAME:
        raise ValueError("S3_BUCKET_NAME environment variable is not set")
        
    if not config.AWS_ACCESS_KEY_ID or not config.AWS_SECRET_ACCESS_KEY:
        raise ValueError("AWS credentials are not set")
        
    # Determine content type if not provided
    if not content_type:
        content_type, _ = mimetypes.guess_type(file_path)
        if not content_type:
            content_type = 'application/octet-stream'
    
    # Create S3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        region_name=config.AWS_REGION
    )
    
    # Run upload in a thread to not block the event loop
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, 
        lambda: _upload_to_s3(s3_client, file_path, s3_key, content_type)
    )

def _upload_to_s3(s3_client, file_path: str, s3_key: str, content_type: str) -> str:
    """
    Upload to S3 synchronously (to be called in a thread)
    """
    try:
        # Upload file to S3 with ExtraArgs for content type
        s3_client.upload_file(
            Filename=file_path,
            Bucket=config.S3_BUCKET_NAME,
            Key=s3_key,
            ExtraArgs={'ContentType': content_type}
        )
        
        # Generate the S3 URL
        return f"https://{config.S3_BUCKET_NAME}.s3.{config.AWS_REGION}.amazonaws.com/{s3_key}"
        
    except ClientError as e:
        raise Exception(f"Error uploading to S3: {str(e)}")
    except Exception as e:
        raise Exception(f"Upload error: {str(e)}")

async def upload_text_to_s3(text_content: str, s3_key: str, content_type: str = 'application/json') -> str:
    """
    Upload text content directly to S3
    
    Args:
        text_content: Text content to upload
        s3_key: S3 object key (path within the bucket)
        content_type: Content type of the text (default: application/json)
        
    Returns:
        S3 URL of the uploaded content
    """
    if not config.S3_BUCKET_NAME:
        raise ValueError("S3_BUCKET_NAME environment variable is not set")
        
    if not config.AWS_ACCESS_KEY_ID or not config.AWS_SECRET_ACCESS_KEY:
        raise ValueError("AWS credentials are not set")
    
    # Create S3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        region_name=config.AWS_REGION
    )
    
    # Run upload in a thread to not block the event loop
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, 
        lambda: _upload_text_to_s3(s3_client, text_content, s3_key, content_type)
    )

def _upload_text_to_s3(s3_client, text_content: str, s3_key: str, content_type: str) -> str:
    """
    Upload text to S3 synchronously (to be called in a thread)
    """
    try:
        # Upload text content directly to S3
        s3_client.put_object(
            Body=text_content,
            Bucket=config.S3_BUCKET_NAME,
            Key=s3_key,
            ContentType=content_type
        )
        
        # Generate the S3 URL
        return f"https://{config.S3_BUCKET_NAME}.s3.{config.AWS_REGION}.amazonaws.com/{s3_key}"
        
    except ClientError as e:
        raise Exception(f"Error uploading to S3: {str(e)}")
    except Exception as e:
        raise Exception(f"Upload error: {str(e)}")