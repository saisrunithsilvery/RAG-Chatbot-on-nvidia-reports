import logging
import boto3
import aiohttp
from botocore.exceptions import NoCredentialsError, ClientError
from pathlib import Path
import os
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Get AWS credentials from environment variables
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("S3_BUCKET", "damg7245-nvidia-reports")
S3_REGION = os.getenv("S3_REGION", "us-east-1")



# Initialize S3 client
s3_client = boto3.client('s3')

# In your startup code
try:
    response = s3_client.list_buckets()
    logger.info(f"Successfully connected to AWS. Available buckets: {[b['Name'] for b in response['Buckets']]}")
except Exception as e:
    logger.error(f"Failed to connect to AWS: {str(e)}")

async def download_from_s3(s3_url: str, local_path: Path):
    """
    Download a file from S3 to a local path
    
    Args:
        s3_url: URL of the S3 object
        local_path: Local path to save the file
    """
    try:
        # Parse the S3 URL to get bucket and key
        parsed_url = urlparse(s3_url)
        
        # Better parsing of S3 URL
        if 's3.amazonaws.com' in parsed_url.netloc:
            # Standard URL format: bucket.s3.amazonaws.com/key
            bucket = parsed_url.netloc.split('.s3.amazonaws.com')[0]
        elif 's3.' in parsed_url.netloc and '.amazonaws.com' in parsed_url.netloc:
            # Regional URL format: bucket.s3.region.amazonaws.com/key
            parts = parsed_url.netloc.split('.')
            if len(parts) >= 4 and parts[1] == 's3':
                bucket = parts[0]
            else:
                # Direct S3 URL: s3.region.amazonaws.com/bucket/key
                bucket = parsed_url.path.lstrip('/').split('/')[0]
                key = '/'.join(parsed_url.path.lstrip('/').split('/')[1:])
                # Adjust the path to exclude the bucket name
                parsed_url = parsed_url._replace(path='/' + key)
        else:
            # Assume bucket name is explicitly provided in your config
            bucket = S3_BUCKET
        
        # Extract the key from the path
        key = parsed_url.path.lstrip('/')
        
        logger.info(f"Downloading from S3 bucket: {bucket}, key: {key}")
        
        # Use boto3 for direct S3 access
        s3_client.download_file(bucket, key, str(local_path))
        
        logger.info(f"File downloaded successfully to {local_path}")
        return local_path
    
    except NoCredentialsError:
        logger.error("No AWS credentials found")
        raise Exception("AWS credentials not available")
    except ClientError as e:
        logger.error(f"AWS client error: {str(e)}")
        raise Exception(f"S3 download error: {str(e)}")
    except Exception as e:
        logger.error(f"Error downloading file from S3: {str(e)}")
        raise Exception(f"Failed to download file: {str(e)}")

    
async def upload_to_s3(local_path: Path, s3_key: str):
    """
    Upload a file to S3
    
    Args:
        local_path: Local path of the file to upload
        s3_key: S3 key where the file will be uploaded
        
    Returns:
        S3 URL of the uploaded file
    """
    try:
        logger.info(f"Uploading file to S3: {local_path} -> {s3_key}")
        
        # Upload the file to S3
        s3_client.upload_file(str(local_path), S3_BUCKET, s3_key)
        
        # Generate the S3 URL
        s3_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{s3_key}"
        
        logger.info(f"File uploaded successfully to {s3_url}")
        return s3_url
    
    except NoCredentialsError:
        logger.error("No AWS credentials found")
        raise Exception("AWS credentials not available")
    except ClientError as e:
        logger.error(f"AWS client error: {str(e)}")
        raise Exception(f"S3 upload error: {str(e)}")
    except Exception as e:
        logger.error(f"Error uploading file to S3: {str(e)}")
        raise Exception(f"Failed to upload file: {str(e)}")