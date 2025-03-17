import re
import logging
import boto3
from pathlib import Path
import requests
import os
import uuid
from datetime import datetime
from urllib.parse import urlparse, unquote

# Set up logging
_log = logging.getLogger(__name__)

def extract_image_name(url):
    """Extract image name from URL, maintaining extension."""
    try:
        parsed = urlparse(url)
        path = unquote(parsed.path)  # Decode URL-encoded characters
        filename = os.path.basename(path)
        
        # If filename has no extension, try to extract from query params
        if not os.path.splitext(filename)[1]:
            return None
            
        # Remove query parameters if present
        filename = filename.split('?')[0]
        
        # Sanitize filename
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
            
        return filename
    except Exception as e:
        _log.warning(f"Error extracting image name from {url}: {e}")
        return None

def download_and_replace_images(md_path):
    """Download images and replace URLs in Markdown content with S3 paths."""
    try:
        # Initialize S3 client
        s3_client = boto3.client('s3')
        bucket_name = "damg7245-datanexus-pro"

        # Read the markdown content
        md_path = Path(md_path)
        if not md_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {md_path}")
            
        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
    
        # Create unique folder name
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        process_folder = f"Web_Extract_{timestamp}_{unique_id}"
    
        # Define S3 paths
        base_s3_path = f"web-extract/{process_folder}"
        images_s3_path = f"{base_s3_path}/images"
        markdown_s3_path = f"{base_s3_path}/markdown"

        # Find all image URLs in markdown
        pattern = r'!\[.*?\]\((https?://[^\s]+)\)'
        matches = re.findall(pattern, md_content)
        
        if not matches:
            _log.info("No images found in markdown content")
            return md_content, None

        # Set up headers for requests
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Accept": "image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": "https://www.google.com",
        }
        
        session = requests.Session()  # Use a session for persistent headers
        
        # Process each image
        for img_url in matches:
            image_name = extract_image_name(img_url)
            if not image_name:
                _log.warning(f"Could not extract valid image name from {img_url}")
                continue
                
            try:
                # Download image
                response = session.get(img_url, headers=headers, stream=True, allow_redirects=True)
                response.raise_for_status()
                
                # Upload image to S3
                s3_image_key = f"{images_s3_path}/{image_name}"
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=s3_image_key,
                    Body=response.content,
                    ContentType=response.headers.get('content-type', 'application/octet-stream')
                )
                
                # Generate the full S3 URL for the image
                s3_image_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_image_key}"
                
                # Replace URL in markdown content with S3 URL
                md_content = md_content.replace(img_url, s3_image_url)
                _log.info(f"Downloaded and replaced: {img_url} -> {s3_image_url}")
                
            except requests.exceptions.HTTPError as http_err:
                _log.warning(f"HTTP error while downloading image {img_url}: {http_err}")
            except requests.exceptions.RequestException as req_err:
                _log.warning(f"Request error while downloading image {img_url}: {req_err}")
            except Exception as e:
                _log.warning(f"Unexpected error processing image {img_url}: {e}")
        
        # Upload markdown content to S3
        markdown_key = f"{markdown_s3_path}/content.md"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=markdown_key,
            Body=md_content.encode('utf-8')
        )
        
        _log.info(f"Uploaded markdown to S3: {markdown_key}")
        
        # Return the base S3 URL for the processed content
        return f"https://{bucket_name}.s3.amazonaws.com/{base_s3_path}/"
        
    except Exception as e:
        _log.error(f"Error processing markdown file: {e}")
        raise