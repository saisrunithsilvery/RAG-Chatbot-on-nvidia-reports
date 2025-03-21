import logging
import tempfile
import os
import time
from pathlib import Path
from utils.s3_utils import download_from_s3, upload_to_s3
from utils.ocr_utils import convert_pdf_to_markdown

logger = logging.getLogger(__name__)

async def process_document(s3_url: str):
    """
    Process a document from S3 URL:
    1. Download PDF from S3
    2. Convert PDF to Markdown using Mistral OCR
    3. Upload Markdown back to S3
    4. Return the S3 URL of the Markdown file
    
    Args:
        s3_url: S3 URL of the PDF document
        
    Returns:
        Dict with status and markdown_url
    """
    try:
        # Extract filename from S3 URL
        filename = s3_url.split("/")[-1]
        base_name = filename.split(".")[0]
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # Download PDF from S3
            logger.info(f"Downloading PDF from S3: {s3_url}")
            pdf_path = temp_dir_path / filename
            print("the pdf", pdf_path)
            print("the s3-url",s3_url)
            await download_from_s3(s3_url, pdf_path)
            
            # Process PDF with Mistral OCR
            logger.info(f"Converting PDF to Markdown: {pdf_path}")
            output_dir = temp_dir_path / "output"
            output_dir.mkdir(exist_ok=True)
            
            markdown_path = await convert_pdf_to_markdown(pdf_path, output_dir)
            
            # Generate timestamp for unique filename
            timestamp = int(time.time())
            unique_filename = f"tmp{timestamp}.md"
            
            # Define S3 upload path
            s3_upload_path = f"mistral-parsed/{base_name}/markdown/{unique_filename}"
            
            # Upload markdown to S3
            logger.info(f"Uploading Markdown to S3: {s3_upload_path}")
            markdown_url = await upload_to_s3(markdown_path, s3_upload_path)
            
            return {
                "status": "success",
                "markdown_url": markdown_url
            }
    
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise Exception(f"Failed to process document: {str(e)}")