import logging
from pathlib import Path
from typing import Dict, Any

from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc import ImageRefMode, PictureItem, TableItem

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

class DoclingConverter:
    def __init__(self):
        # Configure PDF pipeline options
        self.pipeline_options = PdfPipelineOptions()
        self.pipeline_options.images_scale = 2.0
        self.pipeline_options.generate_table_images = True
        self.pipeline_options.generate_picture_images = True
        
        # Initialize document converter
        self.doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=self.pipeline_options)
            }
        )

    def process_pdf(self, pdf_path: Path, output_dir: Path) -> Dict[str, Any]:
        """
        Process a single PDF file and convert to markdown with images
        
        Args:
            pdf_path: Path to input PDF file
            output_dir: Directory for output files
        
        Returns:
            Dictionary containing processing results
        """
        try:
            # Create output directories
            markdown_dir = output_dir / "markdown"
            images_dir = output_dir / "images"
            markdown_dir.mkdir(parents=True, exist_ok=True)
            images_dir.mkdir(parents=True, exist_ok=True)

            # Convert PDF
            conv_results = self.doc_converter.convert_all([pdf_path], raises_on_error=False)
            
            for conv_res in conv_results:
                if conv_res.status == ConversionStatus.SUCCESS:
                    # Generate base filename
                    base_filename = conv_res.input.file.stem
                    
                    # Save markdown with embedded images
                    markdown_content = conv_res.document.export_to_markdown(
                        image_mode=ImageRefMode.EMBEDDED
                    )
                    markdown_path = markdown_dir / f"{base_filename}.md"
                    markdown_path.write_text(markdown_content)
                    
                    # Export tables and images
                    table_count = 0
                    image_count = 0
                    
                    for element, _ in conv_res.document.iterate_items():
                        if isinstance(element, TableItem):
                            table_count += 1
                            image_path = images_dir / f"{base_filename}-table-{table_count}.png"
                            element.image.pil_image.save(image_path, "PNG")
                        
                        if isinstance(element, PictureItem):
                            image_count += 1
                            image_path = images_dir / f"{base_filename}-image-{image_count}.png"
                            element.image.pil_image.save(image_path, "PNG")
                    
                    return {
                        'status': 'success',
                        'markdown_path': markdown_path,
                        'tables': table_count,
                        'images': image_count
                    }
                
                elif conv_res.status == ConversionStatus.PARTIAL_SUCCESS:
                    error_msg = "Document was partially converted with errors"
                    logger.warning(f"{error_msg}: {conv_res.errors}")
                    return {'status': 'partial_success', 'message': error_msg}
                
                else:
                    error_msg = "Conversion failed"
                    logger.error(error_msg)
                    return {'status': 'error', 'message': error_msg}
                    
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            return {'status': 'error', 'message': str(e)}



