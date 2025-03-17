import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import boto3
import uuid
from datetime import datetime
import fitz  # PyMuPDF for PDF processing
import re

# Create logs directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "parsing.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PdfConverter:
    def __init__(self, bucket_name: str = "damg7245-datanexus-pro"):
        """Initialize PdfConverter with S3 bucket configuration"""
        self.s3_client = boto3.client('s3')
        self.bucket_name = bucket_name

    def get_s3_url(self, s3_key: str) -> str:
        """Generate an S3 URL for a given key"""
        return f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"

    def upload_to_s3(self, local_path: Path, s3_key: str) -> bool:
        """Upload a file to S3 with error handling"""
        try:
            if not local_path.exists():
                logger.error(f"File not found: {local_path}")

                return False

            self.s3_client.upload_file(str(local_path), self.bucket_name, s3_key)
            logger.info(f"Successfully uploaded {local_path} to s3://{self.bucket_name}/{s3_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload {local_path} to S3: {str(e)}")
            return False

    def extract_and_upload_images(
        self,
        pdf_document: fitz.Document,
        images_dir: Path,
        base_filename: str,
        base_s3_path: str
    ) -> List[Dict[str, Any]]:
        """Extract embedded images from PDF and upload to S3"""
        image_info = []
        images_dir.mkdir(parents=True, exist_ok=True)

        try:
            for page_num, page in enumerate(pdf_document):
                # Get a list of all images on the page
                image_list = page.get_images()

                for img_idx, img in enumerate(image_list):
                    try:
                        # Get the xref of the image
                        xref = img[0]

                        # Extract image info
                        base_image = pdf_document.extract_image(xref)
                        if base_image:
                            image_bytes = base_image["image"]
                            image_ext = base_image["ext"]

                            # Save image
                            image_filename = f"{base_filename}_image_{page_num + 1}_{img_idx + 1}.{image_ext}"
                            image_path = images_dir / image_filename

                            with open(image_path, 'wb') as img_file:
                                img_file.write(image_bytes)

                            # Upload to S3
                            image_s3_key = f"{base_s3_path}/images/{image_filename}"
                            if self.upload_to_s3(image_path, image_s3_key):
                                # Get the bounding box of the image (if available)
                                bbox = img[1:5]  # x0, y0, x1, y1
                                image_info.append({
                                    'page': page_num,
                                    'bbox': bbox,
                                    'type': 'image',
                                    's3_url': self.get_s3_url(image_s3_key)
                                })
                                logger.info(f"Successfully extracted and uploaded image {img_idx + 1} from page {page_num + 1}")

                    except Exception as e:
                        logger.error(f"Failed to process image {img_idx} on page {page_num}: {str(e)}")
                        continue

            return sorted(image_info, key=lambda x: (x['page'], x['bbox'][1]))

        except Exception as e:
            logger.error(f"Error in extract_and_upload_images: {str(e)}")
            return []     
    def convert_table_to_markdown(self, table_dict: Dict) -> str:
        """Convert table data to markdown format"""
        try:
            if not table_dict or 'cells' not in table_dict:
                return ""

            cells = table_dict['cells']
            rows = {}

            # Group cells by row
            for cell in cells:
                row_num = cell['bbox'][1]  # y-coordinate of top
                if row_num not in rows:
                    rows[row_num] = []

                rows[row_num].append(cell)

            # Sort rows by y-coordinate
            sorted_rows = sorted(rows.items())

            # Build markdown table
            markdown_rows = []

            # Header row
            if sorted_rows:
                header = sorted_rows[0][1]
                header_row = [cell['text'].strip() for cell in sorted(header, key=lambda x: x['bbox'][0])]
                markdown_rows.append("| " + " | ".join(header_row) + " |")
                markdown_rows.append("| " + " | ".join(['---'] * len(header_row)) + " |")

                # Data rows
                for _, row in sorted_rows[1:]:
                    sorted_cells = sorted(row, key=lambda x: x['bbox'][0])
                    row_data = [cell['text'].strip() for cell in sorted_cells]
                    markdown_rows.append("| " + " | ".join(row_data) + " |")

            return "\n".join(markdown_rows) + "\n\n"

        except Exception as e:
            logger.error(f"Error converting table to markdown: {str(e)}")
            return ""

    def detect_table(self, page: fitz.Page, block: Dict) -> bool:
        """Detect if a block contains a table structure"""
        try:
            if block.get("lines", []):
                # Check for consistent vertical alignment of words
                x_positions = []
                for line in block["lines"]:
                    for span in line["spans"]:
                        x_positions.append(span["origin"][0])

                # If we have multiple lines with consistent x-positions, likely a table
                unique_x = sorted(set(x_positions))

                if len(unique_x) > 2 and len(x_positions) / len(unique_x) > 2:
                    return True

            return False

        except Exception as e:
            logger.error(f"Error in detect_table: {str(e)}")
            return False

    def extract_text_with_layout(
        self,
        pdf_document: fitz.Document,
        image_info: List[Dict]
    ) -> str:
        """Extract text while preserving layout and image positions"""
        try:
            markdown_content = []

            for page_num, page in enumerate(pdf_document):
                page_dict = page.get_text("dict")
                blocks = sorted(page_dict["blocks"], key=lambda b: (b["bbox"][1], b["bbox"][0]))

                # Track current y-position for image placement
                current_y = 0

                for block in blocks:
                    # Get block's vertical position
                    block_y = block["bbox"][1]

                    # Insert any images that should appear before this block
                    page_images = [img for img in image_info if img['page'] == page_num and 
                                current_y <= img['bbox'][1] < block_y]

                    for img in sorted(page_images, key=lambda x: x['bbox'][1]):
                        markdown_content.append(f"\n![image]({img['s3_url']})\n")
                        image_info.remove(img)

                    if block["type"] == 0:  # Text
                        if self.detect_table(page, block):

  
                            # Convert table to markdown
                            table_md = self.convert_table_to_markdown(block)
                            if table_md:
                                markdown_content.append(table_md)
                        else:
                            # Process text
                            text_content = []
                            for line in block["lines"]:
                                try:
                                    text = " ".join(span["text"] for span in line["spans"])
                                    font_size = line["spans"][0]["size"]

                                    if font_size > 14:
                                        text_content.append(f"## {text}\n")
                                    else:
                                        text_content.append(f"{text}\n")
                                except Exception as e:
                                    logger.error(f"Error processing line: {str(e)}")
                                    continue

                            markdown_content.append("".join(text_content))

                    current_y = block["bbox"][3]  # Update current y-position

                # Add any remaining images for this page
                remaining_images = [img for img in image_info if img['page'] == page_num]
                for img in sorted(remaining_images, key=lambda x: x['bbox'][1]):
                    markdown_content.append(f"\n![image]({img['s3_url']})\n")
                    image_info.remove(img)

                # Add page break between pages
                markdown_content.append("\n---\n")

            return "".join(markdown_content)

        except Exception as e:
            logger.error(f"Error in extract_text_with_layout: {str(e)}")
            return ""
 
    def process_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Process a single PDF file"""
        try:
            # Create base directories
            output_dir = Path("output")
            markdown_dir = output_dir / "markdown"
            images_dir = output_dir / "images"

            for dir_path in [markdown_dir, images_dir]:
                dir_path.mkdir(parents=True, exist_ok=True)

            # Create unique folder name for S3
            unique_id = str(uuid.uuid4())[:8]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            process_folder = f"PDF_Extract_{timestamp}_{unique_id}"
            base_s3_path = f"pdf-extract/{process_folder}"

            logger.info(f"Processing PDF: {pdf_path}")
            logger.info(f"Output folder: {process_folder}")

            try:
                pdf_document = fitz.open(pdf_path)
            except Exception as e:
                logger.error(f"Failed to open PDF: {str(e)}")
                return {'status': 'error', 'message': f"Failed to open PDF: {str(e)}"}

            try:
                base_filename = pdf_path.stem

                # First extract and upload images
                image_info = self.extract_and_upload_images(
                    pdf_document, images_dir, base_filename, base_s3_path
                )

                # Then extract text with layout and image positions
                markdown_content = self.extract_text_with_layout(pdf_document, image_info)

                # Save and upload markdown
                markdown_path = markdown_dir / f"{base_filename}.md"

 
                # Then extract text with layout and image positions
                try:
                    markdown_path.write_text(markdown_content)
                    logger.info(f"Saved markdown to {markdown_path}")
                except Exception as e:
                    logger.error(f"Failed to save markdown: {str(e)}")
                    return {'status': 'error', 'message': f"Failed to save markdown: {str(e)}"}

                markdown_s3_key = f"{base_s3_path}/markdown/content.md"
                if not self.upload_to_s3(markdown_path, markdown_s3_key):
                    return {'status': 'error', 'message': "Failed to upload markdown to S3"}

                return {
                    'status': 'success',
                    'markdown_path': str(markdown_path),
                    'markdown_content': markdown_content,
                    'markdown_s3_url': self.get_s3_url(markdown_s3_key),
                    's3_base_path': f"s3://{self.bucket_name}/{base_s3_path}",
                    'images': [{
                        'type': img['type'],
                        's3_url': img['s3_url']
                    } for img in image_info]
                }

            finally:
                try:
                    pdf_document.close()
                except:
                    pass

        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            return {'status': 'error', 'message': str(e)}