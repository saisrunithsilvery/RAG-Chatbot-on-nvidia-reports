import os
import json
import base64
from typing import Dict, Any
import asyncio
from mistralai import Mistral
from mistralai import Mistral, DocumentURLChunk
from mistralai.models import OCRResponse

import config

async def process_file_with_mistral_ocr(file_path: str) -> Dict[str, Any]:
    """
    Process a file using Mistral OCR
    
    Args:
        file_path: Path to the local file or URL to process
        
    Returns:
        Dictionary containing OCR results
    """
    # Check if the path is a URL or local file
    is_url = file_path.startswith(('http://', 'https://'))
    
    if not is_url:
        # Validate that the local file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check file size for local files
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > config.MAX_FILE_SIZE_MB:
            raise ValueError(f"File size ({file_size_mb:.2f} MB) exceeds maximum allowed size ({config.MAX_FILE_SIZE_MB} MB)")
    
    # Initialize Mistral client
    if not config.MISTRAL_API_KEY:
        raise ValueError("MISTRAL_API_KEY is not set")
        
    client = Mistral(api_key=config.MISTRAL_API_KEY)
    
    # Run OCR processing in a separate thread to not block the event loop
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: _run_mistral_ocr(client, file_path))
    
def _run_mistral_ocr(client: Mistral, file_path: str) -> Dict[str, Any]:
    """
    Run Mistral OCR synchronously (to be called in a thread)
    """
    try:
        # Check if the file_path is a URL or local path
        is_url = file_path.startswith(('http://', 'https://'))
        
        if is_url:
            # Use document_url for URLs
            ocr_response = client.ocr.process(
                model="mistral-ocr-latest",
                document={
                    "type": "document_url",
                    "document_url": file_path
                },
                include_image_base64=True
            )
        else:
            # For local files, read the file and use base64 encoding
            with open(file_path, "rb") as f:
                file_content = f.read()
                base64_encoded = base64.b64encode(file_content).decode("utf-8")
                
            ocr_response = client.ocr.process(
                model="mistral-ocr-latest",
                document={
                    "type": "document_base64",
                    "document_base64": base64_encoded
                },
                include_image_base64=True
            )
        
        # Debug the response structure
        print(f"OCR Response type: {type(ocr_response)}")
        print(f"OCR Response attributes: {dir(ocr_response)}")
        
        # Extract relevant information from the response with careful attribute checking
        result = {
            "text": "",
            "pages": []
        }
        
        # Get the full text if available
        if hasattr(ocr_response, 'text'):
            result["text"] = ocr_response.text
        elif hasattr(ocr_response, 'full_text'):
            result["text"] = ocr_response.full_text
        elif hasattr(ocr_response, 'content') and hasattr(ocr_response.content, 'text'):
            result["text"] = ocr_response.content.text
        
        # Add page information if available
        if hasattr(ocr_response, 'pages') and ocr_response.pages:
            for page in ocr_response.pages:
                page_info = {}
                
                # Check for each attribute before accessing
                if hasattr(page, 'page_num'):
                    page_info["page_num"] = page.page_num
                elif hasattr(page, 'number'):
                    page_info["page_num"] = page.number
                
                if hasattr(page, 'width'):
                    page_info["width"] = page.width
                if hasattr(page, 'height'):
                    page_info["height"] = page.height
                
                # Add extracted blocks if available
                if hasattr(page, 'blocks') and page.blocks:
                    page_info["blocks"] = []
                    for block in page.blocks:
                        block_info = {}
                        if hasattr(block, 'text'):
                            block_info["text"] = block.text
                        if hasattr(block, 'bbox'):
                            block_info["bbox"] = block.bbox
                        
                        if block_info:  # Only add if we have some information
                            page_info["blocks"].append(block_info)
                
                # Check if we have page text
                if hasattr(page, 'text'):
                    page_info["text"] = page.text
                
                if page_info:  # Only add if we have some information
                    result["pages"].append(page_info)
        
        # If we still don't have any text content, try to extract the raw JSON
        if not result["text"] and hasattr(ocr_response, 'model_dump'):
            try:
                # Try to get the raw response as a dict
                response_dict = ocr_response.model_dump()
                print(f"Response dict keys: {response_dict.keys()}")
                
                # Look for text in common locations in the dict
                if "text" in response_dict:
                    result["text"] = response_dict["text"]
                elif "full_text" in response_dict:
                    result["text"] = response_dict["full_text"]
                
                # Try to find pages data
                if "pages" in response_dict and not result["pages"]:
                    for page_data in response_dict["pages"]:
                        result["pages"].append(page_data)
                
                # If we still don't have text, but have pages with text
                if not result["text"] and result["pages"]:
                    page_texts = []
                    for page in result["pages"]:
                        if "text" in page:
                            page_texts.append(page["text"])
                    if page_texts:
                        result["text"] = "\n\n".join(page_texts)
            except Exception as e:
                print(f"Error extracting from model_dump: {str(e)}")
        
        # If we still have no content, return the raw response as a string
        if not result["text"] and not result["pages"]:
            result["raw_response"] = str(ocr_response)
            
        return result
        
    except Exception as e:
        raise Exception(f"OCR processing error: {str(e)}")