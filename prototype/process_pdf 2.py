import os
from Docling import PdfParser
from typing import Dict


def process_pdf_with_docling(pdf_path: str, output_dir: str = "output") -> Dict:
    """
    Process a PDF using Docling to extract text, tables, and images.

    Args:
        pdf_path (str): Path to the PDF file.
        output_dir (str): Directory to save output files.

    Returns:
        Dict: Extracted content including text, tables, and images.
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Initialize Docling parser
    parser = PdfParser()

    # Parse the PDF
    parsed_pdf = parser.parse(pdf_path)

    # Extract text and tables
    text = parser.to_text(parsed_pdf)       # Extract all text
    tables = parser.to_tables(parsed_pdf)   # Extract all tables

    # Save extracted text to a Markdown file
    pdf_name = os.path.basename(pdf_path).replace(".pdf", "")
    markdown_path = os.path.join(output_dir, f"{pdf_name}.md")
    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(text)

    # Extract images
    image_dir = os.path.join(output_dir, f"{pdf_name}_images")
    os.makedirs(image_dir, exist_ok=True)
    parser.save_images(parsed_pdf, image_dir)

    return {
        "text": text,
        "tables": tables,
        "images": image_dir,
        "markdown_path": markdown_path,
    }
