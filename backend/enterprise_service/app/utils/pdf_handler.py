import logging
from pathlib import Path
import json
import zipfile
import pandas as pd
import traceback
import tempfile
import boto3
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


def convert_json_to_markdown(data):
    """
    Universal converter for Adobe PDF Extract API JSON to Markdown.
    Handles any PDF document structure with robust error handling.
    """
    markdown_content = []
    
    def clean_text(text):
        """Clean and normalize text content"""
        if not text:
            return ""
        # Remove multiple spaces and normalize whitespace
        text = ' '.join(text.strip().split())
        # Remove common PDF artifacts
        text = text.replace('_x000D_', '')
        return text

    def detect_heading_level(text):
        """Detect if text is a heading and determine its level"""
        if not text:
            return False, 0
            
        text = text.strip()
        
        # H1 indicators
        if any(indicator in text for indicator in ['White Paper', 'Guide', 'Documentation']):
            return True, 1
            
        # H2 indicators (main sections)
        if text.isupper() or any(text.lower().startswith(word) for word in 
            ['overview', 'introduction', 'conclusion', 'chapter', 'section']):
            return True, 2
            
        # H3 indicators (subsections)
        if text.endswith(':') or ('data' in text.lower() and len(text.split()) <= 4):
            return True, 3
            
        return False, 0

    def format_list_item(text):
        """Format list items with proper markdown"""
        text = clean_text(text)
        if not text:
            return ""
            
        if text.startswith('•') or text.startswith('-'):
            return f"* {text[1:].strip()}\n"
        elif text[0].isdigit() and '.' in text[:3]:
            parts = text.split('.', 1)
            if len(parts) > 1:
                return f"{parts[0]}. {parts[1].strip()}\n"
        return text + "\n\n"

    # Process elements
    if 'elements' in data:
        for element in data['elements']:
            # Get text content
            text = element.get('Text', '')
            if not text:
                continue

            text = clean_text(text)
            
            # Skip lone numbers (likely page numbers)
            if text.isdigit():
                continue

            # Handle lists
            if text.startswith('•') or text.startswith('-') or (text[0].isdigit() and '.' in text[:3]):
                markdown_content.append(format_list_item(text))
                continue

            # Detect headings
            is_heading, level = detect_heading_level(text)
            if is_heading:
                markdown_content.append(f"{'#' * level} {text}\n\n")
                continue

            # Handle regular paragraphs
            if len(text.split()) > 1:  # Only add if more than one word
                markdown_content.append(f"{text}\n\n")

    # Join and clean up the final markdown
    result = ''.join(markdown_content)
    
    # Clean up excessive newlines
    while '\n\n\n' in result:
        result = result.replace('\n\n\n', '\n\n')
    
    # Clean up list formatting
    result = result.replace('* \n', '* ')
    
    return result.strip()


def convert_table_to_markdown(df):
    """Convert pandas DataFrame to markdown table"""
    markdown_lines = []
    
    # Headers
    headers = [str(h).replace('_x000D_', '').strip() for h in df.columns.tolist()]
    markdown_lines.append("| " + " | ".join(headers) + " |")
    markdown_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    
    # Data rows
    for _, row in df.iterrows():
        # Clean up cell content
        cells = [str(cell).replace('_x000D_', '').strip() for cell in row]
        markdown_lines.append("| " + " | ".join(cells) + " |")
    
    return "\n".join(markdown_lines)


def process_zip(zip_path: str) -> str:
    """Handler function to process the extracted ZIP file and upload to S3"""
    s3_client = boto3.client('s3')
    bucket_name = "damg7245-datanexus-pro"
    
    # Create unique folder name
    unique_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    process_folder = f"PDF_Extract_{timestamp}_{unique_id}"
    
    # Define S3 paths
    base_s3_path = f"pdf-extract/{process_folder}"
    images_s3_path = f"{base_s3_path}/images"
    markdown_s3_path = f"{base_s3_path}/markdown"

    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        
        try:
            # Extract ZIP contents
            logger.info(f"Extracting ZIP file: {zip_path}")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir_path)

            final_content = []

            # Process structured JSON
            json_files = list(temp_dir_path.glob('*.json'))
            if json_files:
                json_file = json_files[0]
                logger.info(f"Found JSON file: {json_file.name}")
                
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        logger.info("JSON structure keys: " + str(list(data.keys())))
                    
                    markdown_text = convert_json_to_markdown(data)
                    if markdown_text.strip():
                        final_content.append(markdown_text)
                        logger.info("Successfully converted JSON to markdown")
                    else:
                        logger.warning("No content extracted from JSON")
                except Exception as e:
                    logger.error(f"Error processing JSON file: {str(e)}")
                    logger.error(traceback.format_exc())

            # Process figures
            figures_dir = temp_dir_path / "figures"
            if figures_dir.exists():
                logger.info("Processing figures...")
                final_content.append("\n## Figures\n")
                for img_file in figures_dir.glob("*"):
                    if img_file.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                        s3_image_key = f"{images_s3_path}/{img_file.name}"
                        # Upload without ACL since bucket uses Object Ownership
                        s3_client.upload_file(
                            str(img_file),
                            bucket_name,
                            s3_image_key
                        )
                        # Generate the full S3 URL for the image
                        s3_image_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_image_key}"
                        logger.info(f"Uploaded image: {s3_image_key}")
                        final_content.append(f"\n![{img_file.stem}]({s3_image_url})\n")

            # Process tables
            tables_dir = temp_dir_path / "tables"
            if tables_dir.exists():
                logger.info("Processing tables...")
                final_content.append("\n## Tables\n")
                
                for xlsx_file in tables_dir.glob("*.xlsx"):
                    try:
                        df = pd.read_excel(xlsx_file)
                        final_content.append(f"\n### {xlsx_file.stem}\n")
                        table_content = convert_table_to_markdown(df)
                        final_content.append(table_content + "\n\n")
                    except Exception as e:
                        logger.error(f"Error processing table {xlsx_file.name}: {str(e)}")

            # Upload markdown content to S3
            markdown_content = ''.join(final_content)
            markdown_content = markdown_content.replace('\r\n', '\n')
            markdown_content = markdown_content.replace('_x000D_', '')
            
            s3_client.put_object(
                Bucket=bucket_name,
                Key=f"{markdown_s3_path}/content.md",
                Body=markdown_content.encode('utf-8')
            )
            logger.info(f"Uploaded markdown to S3: {markdown_s3_path}/content.md")

            # Cleanup
            logger.info("Cleaning up...")
            Path(zip_path).unlink()
            logger.info("Cleanup completed successfully")

            return f"https://{bucket_name}.s3.amazonaws.com/{base_s3_path}/"

        except Exception as e:
            logger.error(f"Error processing ZIP file: {str(e)}")
            raise