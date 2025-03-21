import logging
import json
import base64
import os
from pathlib import Path
from mistralai import Mistral, DocumentURLChunk
from mistralai.models import OCRResponse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Mistral API configuration
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_OCR_MODEL = os.getenv("MISTRAL_OCR_MODEL", "mistral-ocr-latest")

# Initialize Mistral client
mistral_client = Mistral(api_key=MISTRAL_API_KEY)

async def convert_pdf_to_markdown(pdf_path: Path, output_dir: Path):
    """
    Convert a PDF document to Markdown using Mistral OCR
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory where output files will be saved
        
    Returns:
        Path to the generated Markdown file
    """
    try:
        logger.info(f"Converting PDF to Markdown: {pdf_path}")
        
        # PDF base name
        pdf_base = pdf_path.stem
        
        # Create output directories
        output_dir.mkdir(exist_ok=True)
        images_dir = output_dir / "images"
        images_dir.mkdir(exist_ok=True)
        
        # Read PDF file
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        # Upload file to Mistral
        logger.info("Uploading file to Mistral API")
        uploaded_file = mistral_client.files.upload(
            file={
                "file_name": pdf_path.name,
                "content": pdf_bytes,
            },
            purpose="ocr"
        )
        
        # Get signed URL
        signed_url = mistral_client.files.get_signed_url(file_id=uploaded_file.id, expiry=1)
        
        # Process with OCR
        logger.info("Processing file with Mistral OCR API")
        ocr_response = mistral_client.ocr.process(
            document=DocumentURLChunk(document_url=signed_url.url),
            model=MISTRAL_OCR_MODEL,
            include_image_base64=True
        )
        
        # Save OCR response (for debugging)
        ocr_json_path = output_dir / "ocr_response.json"
        with open(ocr_json_path, "w", encoding="utf-8") as json_file:
            json.dump(ocr_response.dict(), json_file, indent=4, ensure_ascii=False)
        
        # Process OCR response and generate Markdown
        logger.info("Generating Markdown from OCR response")
        global_counter = 1
        updated_markdown_pages = []
        
        for page in ocr_response.pages:
            updated_markdown = page.markdown
            for image_obj in page.images:
                # Convert base64 to image
                base64_str = image_obj.image_base64
                if base64_str.startswith("data:"):
                    base64_str = base64_str.split(",", 1)[1]
                image_bytes = base64.b64decode(base64_str)
                
                # Image extensions
                ext = Path(image_obj.id).suffix if Path(image_obj.id).suffix else ".png"
                new_image_name = f"{pdf_base}_img_{global_counter}{ext}"
                global_counter += 1
                
                # Save image
                image_output_path = images_dir / new_image_name
                with open(image_output_path, "wb") as f:
                    f.write(image_bytes)
                
                # Update markdown with wikilink
                updated_markdown = updated_markdown.replace(
                    f"![{image_obj.id}]({image_obj.id})",
                    f"![[{new_image_name}]]"
                )
            updated_markdown_pages.append(updated_markdown)
        
        # Join all pages and save markdown
        final_markdown = "\n\n".join(updated_markdown_pages)
        output_markdown_path = output_dir / "output.md"
        with open(output_markdown_path, "w", encoding="utf-8") as md_file:
            md_file.write(final_markdown)
        
        logger.info(f"Markdown generated successfully at {output_markdown_path}")
        return output_markdown_path
    
    except Exception as e:
        logger.error(f"Error converting PDF to Markdown: {str(e)}")
        raise Exception(f"OCR conversion failed: {str(e)}")