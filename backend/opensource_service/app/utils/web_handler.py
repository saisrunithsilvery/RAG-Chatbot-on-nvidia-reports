import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import json
import re
import logging
import base64
import uuid
import boto3
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from markdown_it import MarkdownIt

# Configure logging
logging.basicConfig(level=logging.INFO)
_log = logging.getLogger(__name__)

def create_session_with_retries():
    """Create requests session with retry strategy and browser-like headers."""
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,  # number of retries
        backoff_factor=1,  # wait 1, 2, 4 seconds between retries
        status_forcelist=[429, 500, 502, 503, 504],  # retry on these status codes
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Add browser-like headers
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    })
    
    return session

def download_image(url, output_dir):
    """Download image from URL with improved error handling and retries."""
    try:
        session = create_session_with_retries()
        
        # Extract filename and create full path
        image_name = extract_image_name(url) or f"image_{uuid.uuid4()}.jpg"
        image_path = output_dir / image_name
        
        # Try to download with retry logic
        response = session.get(url, stream=True, timeout=10)
        response.raise_for_status()
        
        # Verify content type is an image
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('image/'):
            _log.warning(f"URL {url} does not point to an image (content-type: {content_type})")
            return None
            
        # Save the image
        with open(image_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        # Verify file was created and has content
        if image_path.stat().st_size == 0:
            _log.error(f"Downloaded image {image_path} is empty")
            image_path.unlink()  # Delete empty file
            return None
            
        return image_path
        
    except requests.exceptions.RequestException as e:
        _log.error(f"Failed to download image from {url}: {str(e)}")
        # Log specific error types for better debugging
        if isinstance(e, requests.exceptions.HTTPError):
            _log.error(f"HTTP Status Code: {e.response.status_code}")
            _log.error(f"Response Headers: {e.response.headers}")
        return None
        
    except Exception as e:
        _log.error(f"Unexpected error downloading image from {url}: {str(e)}")
        return None

def upload_to_s3(file_path, s3_path, bucket_name):
    """Upload file to S3 with improved error handling and metadata."""
    try:
        s3_client = boto3.client('s3')
        
        # Determine content type
        content_type = 'text/markdown'
        if str(file_path).lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            content_type = f'image/{Path(file_path).suffix[1:].lower()}'
        
        # Upload with metadata
        s3_client.upload_file(
            str(file_path), 
            bucket_name, 
            s3_path,
            ExtraArgs={
                'ContentType': content_type,
                'Metadata': {
                    'uploaded_at': datetime.now().isoformat(),
                    'original_filename': Path(file_path).name
                }
            }
        )
        
        # Return public URL instead of s3:// protocol
        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_path}"
        _log.info(f"Successfully uploaded {file_path} to {s3_url}")
        return s3_url
        
    except Exception as e:
        _log.error(f"Failed to upload {file_path} to S3: {str(e)}")
        return None

def find_image_urls(soup, base_url=None):
    """Find all image URLs in HTML content using BeautifulSoup with improved URL handling."""
    images = []
    for img in soup.find_all('img'):
        src = img.get('src')
        if src:
            if src.startswith('data:'):
                continue
                
            # Handle relative URLs
            if base_url and not src.startswith(('http://', 'https://')):
                src = urljoin(base_url, src)
                
            # Validate URL format
            try:
                parsed = urlparse(src)
                if all([parsed.scheme, parsed.netloc]):
                    images.append(src)
            except Exception as e:
                _log.warning(f"Invalid image URL {src}: {str(e)}")
                
    return images

def extract_image_name(url):
    """Extract image name from URL with improved handling."""
    try:
        parsed = urlparse(url)
        path = parsed.path
        
        # Get the filename from the path
        filename = Path(path).name
        
        # If filename has no extension, return None
        if '.' not in filename:
            return None
            
        # Clean the filename
        filename = filename.lower()  # normalize to lowercase
        filename = ''.join(c for c in filename if c.isalnum() or c in '._-')  # remove special chars
        
        return filename if filename else None
        
    except Exception as e:
        _log.error(f"Error extracting image name from {url}: {str(e)}")
        return None

def convert_to_markdown(soup):
    """Convert HTML to Markdown with improved formatting."""
    markdown = []
    
    # Process images first to ensure they're included
    for img in soup.find_all('img'):
        src = img.get('src', '')
        alt = img.get('alt', '') or 'Image'  # Default alt text if none provided
        if src:
            markdown.append(f"![{alt}]({src})\n\n")
    
    # Handle headers
    for i in range(1, 7):
        for header in soup.find_all(f'h{i}'):
            markdown.append(f"{'#' * i} {header.get_text().strip()}\n\n")
    
    # Handle paragraphs
    for p in soup.find_all('p'):
        # Skip paragraphs that only contain images
        if not p.find_all('img'):
            text = p.get_text().strip()
            if text:
                markdown.append(f"{text}\n\n")
    
    # Handle lists
    for ul in soup.find_all('ul'):
        for li in ul.find_all('li'):
            markdown.append(f"* {li.get_text().strip()}\n")
        markdown.append("\n")
    
    for ol in soup.find_all('ol'):
        for i, li in enumerate(ol.find_all('li'), 1):
            markdown.append(f"{i}. {li.get_text().strip()}\n")
        markdown.append("\n")
    
    # Handle links
    for a in soup.find_all('a'):
        href = a.get('href', '')
        text = a.get_text().strip()
        if href and text:
            markdown.append(f"[{text}]({href})\n\n")
    
    return ''.join(markdown)

def process_html_with_docling(html_path):
   
    """Convert HTML to Markdown with image processing and S3 upload."""
    try:
        bucket_name = "damg7245-datanexus-pro"
        
        # Create output directory structure
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)

        # Read and parse HTML content
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract base URL from HTML if available
        base_tag = soup.find('base')
        base_url = base_tag.get('href') if base_tag else None
        
        # Process images first
        image_urls = find_image_urls(soup, base_url)
        image_mappings = {}
        
        # Create unique folder name for S3
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        process_folder = f"web_extract_{timestamp}_{unique_id}"
        base_s3_path = f"web-extract/{process_folder}"
        
        # Download and upload images
        for img_url in image_urls:
            try:
                # Download image
                local_image_path = download_image(img_url, images_dir)
                if local_image_path:
                    # Upload to S3
                    s3_image_path = f"{base_s3_path}/images/{local_image_path.name}"
                    s3_url = upload_to_s3(local_image_path, s3_image_path, bucket_name)
                    if s3_url:
                        image_mappings[img_url] = s3_url
                        
                        # Update all matching image sources in the HTML
                        for img in soup.find_all('img', src=img_url):
                            img['src'] = s3_url
                        
                        # Log successful mapping
                        _log.info(f"Image mapped: {img_url} -> {s3_url}")
            except Exception as e:
                _log.error(f"Failed to process image {img_url}: {str(e)}")
        
        # Log image processing summary
        _log.info(f"Processed {len(image_mappings)} images successfully")
        _log.info(f"Image mappings: {json.dumps(image_mappings, indent=2)}")
        
        # Convert to Markdown after all images are processed
        markdown_content = convert_to_markdown(soup)
        
        # Save Markdown locally
        markdown_path = output_dir / "content.md"
        with open(markdown_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # Upload Markdown to S3
        s3_markdown_path = f"{base_s3_path}/markdown/content.md"
        s3_markdown_url = upload_to_s3(markdown_path, s3_markdown_path, bucket_name)
        
        return f"https://{bucket_name}.s3.amazonaws.com/{s3_markdown_path}"
        
    except Exception as e:
        _log.error(f"Error in conversion process: {str(e)}")
        raise