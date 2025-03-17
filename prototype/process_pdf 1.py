# from docling.document_converter import DocumentConverter
# # from docling.datamodel.base_models import InputFormat
# # from docling.document_converter import PdfFormatOption
# import os
# from typing import Dict


# def process_pdf_with_docling(pdf_path: str, output_dir: str = "output") -> Dict:
#     """
#     Process a PDF using Docling's DocumentConverter to extract text, tables, and images.

#     Args:
#         pdf_path (str): Path to the input PDF file.
#         output_dir (str): Directory to save extracted content.

#     Returns:
#         Dict: A dictionary containing extracted text, tables, and image directory.
#     """
#     # Create output directory
#     os.makedirs(output_dir, exist_ok=True)
#     pdf_name = os.path.basename(pdf_path).replace(".pdf", "")

#     # Initialize DocumentConverter
#     converter = DocumentConverter()

#     # Convert the PDF
#     document = converter.convert(pdf_path)
#     if not document:
#         raise ValueError("Failed to convert PDF. The document is empty.")

#     # Extract text
#     text = document.get_text() if document.has_text() else "No text found."

#     # Extract tables
#     tables = document.get_tables() if document.has_tables() else []

#     # Extract images
#     image_dir = os.path.join(output_dir, f"{pdf_name}_images")
#     os.makedirs(image_dir, exist_ok=True)
#     document.save_images(image_dir)

#     # Save Markdown content
#     markdown_path = save_markdown(text, tables, output_dir, pdf_name)

#     return {
#         "text": text,
#         "tables": tables,
#         "images": image_dir,
#         "markdown_path": markdown_path,
#     }


# def save_markdown(text: str, tables: list, output_dir: str, pdf_name: str) -> str:
#     """
#     Save extracted content as a Markdown file.

#     Args:
#         text (str): Extracted text content.
#         tables (list): Extracted table content.
#         output_dir (str): Directory to save the Markdown file.
#         pdf_name (str): Name of the original PDF file.

#     Returns:
#         str: Path to the saved Markdown file.
#     """
#     markdown_path = os.path.join(output_dir, f"{pdf_name}.md")
#     with open(markdown_path, "w", encoding="utf-8") as f:
#         f.write("# Extracted Content\n\n")
#         f.write("## Text\n")
#         f.write(text + "\n\n")

#         if tables:
#             f.write("## Tables\n")
#             for i, table in enumerate(tables, start=1):
#                 f.write(f"### Table {i}\n")
#                 f.write(format_table(table))
#                 f.write("\n\n")

#     return markdown_path


# def format_table(table: list) -> str:
#     """
#     Format a table as Markdown.

#     Args:
#         table (list): Table data as a list of rows.

#     Returns:
#         str: Markdown-formatted table.
#     """
#     if not table or len(table) < 1:
#         return ""

#     headers = [str(cell).strip() for cell in table[0]]
#     markdown_table = []
#     markdown_table.append("| " + " | ".join(headers) + " |")
#     markdown_table.append("|" + "|".join(["---" for _ in headers]) + "|")

#     for row in table[1:]:
#         markdown_table.append("| " + " | ".join(str(cell).strip() for cell in row) + " |")

#     return "\n".join(markdown_table)



# from docling.document_converter import DocumentConverter
# from docling.datamodel.document import TextItem, TableItem
# import os
# from typing import Dict
# import pandas as pd

# def process_pdf_with_docling(pdf_path: str, output_dir: str = "output") -> Dict:
#     """
#     Process a PDF using Docling's DocumentConverter to extract text, tables, and images.

#     Args:
#         pdf_path (str): Path to the input PDF file.
#         output_dir (str): Directory to save extracted content.

#     Returns:
#         Dict: A dictionary containing extracted text, tables, and image directory.
#     """
#     # Create output directory
#     os.makedirs(output_dir, exist_ok=True)
#     pdf_name = os.path.basename(pdf_path).replace(".pdf", "")

#     # Initialize DocumentConverter
#     converter = DocumentConverter()

#     # Convert the PDF
#     conversion_result = converter.convert(pdf_path)
#     if not conversion_result or not conversion_result.document:
#         raise ValueError("Failed to convert PDF. The document is empty.")

#     # Get the document
#     doc = conversion_result.document

#     # Extract text
#     text_content = []
#     tables = []
    
#     # Iterate through document items
#     for item, level in doc.iterate_items():
#         if isinstance(item, TextItem):
#             text_content.append(item.text)
#         elif isinstance(item, TableItem):
#             table_df = item.export_to_dataframe()
#             if not table_df.empty:
#                 tables.append(table_df)

#     # Join all text content
#     text = "\n".join(text_content)

#     # Create image directory
#     image_dir = os.path.join(output_dir, f"{pdf_name}_images")
#     os.makedirs(image_dir, exist_ok=True)

#     # Save as markdown
#     markdown_path = save_markdown(text, tables, output_dir, pdf_name)

#     return {
#         "text": text,
#         "tables": tables,
#         "images": image_dir,
#         "markdown_path": markdown_path,
#     }

# def save_markdown(text: str, tables: list, output_dir: str, pdf_name: str) -> str:
#     """
#     Save extracted content as a Markdown file.

#     Args:
#         text (str): Extracted text content.
#         tables (list): List of pandas DataFrames containing table data.
#         output_dir (str): Directory to save the Markdown file.
#         pdf_name (str): Name of the original PDF file.

#     Returns:
#         str: Path to the saved Markdown file.
#     """
#     markdown_path = os.path.join(output_dir, f"{pdf_name}.md")
#     with open(markdown_path, "w", encoding="utf-8") as f:
#         f.write("# Extracted Content\n\n")
#         f.write("## Text\n")
#         f.write(text + "\n\n")

#         if tables:
#             f.write("## Tables\n")
#             for i, table_df in enumerate(tables, start=1):
#                 f.write(f"### Table {i}\n")
#                 f.write(table_df.to_markdown(index=False))
#                 f.write("\n\n")

#     return markdown_path

from docling.document_converter import DocumentConverter
from docling.datamodel.document import TextItem, TableItem
from docling.pdf_pipeline_options import PdfPipelineOptions
from docling.datamodel.document import generate_multimodal_pages
from PIL import Image
import os
import pandas as pd
from typing import Dict, List


def process_pdf_with_docling(pdf_path: str, output_dir: str = "output") -> Dict:
    """
    Process a PDF using Docling's DocumentConverter to extract text, tables, and images.

    Args:
        pdf_path (str): Path to the input PDF file.
        output_dir (str): Directory to save extracted content.

    Returns:
        Dict: A dictionary containing extracted content (text, tables, and images) in order.
    """
    os.makedirs(output_dir, exist_ok=True)
    pdf_name = os.path.basename(pdf_path).replace(".pdf", "")

    # Configure the pipeline for images
    pipeline_options = PdfPipelineOptions()
    pipeline_options.generate_page_images = True  # Enable image generation
    pipeline_options.images_scale = 2  # Adjust the resolution if necessary

    # Initialize DocumentConverter
    converter = DocumentConverter(options=pipeline_options)

    # Convert the PDF
    conversion_result = converter.convert(pdf_path)
    if not conversion_result or not conversion_result.document:
        raise ValueError("Failed to convert PDF. The document is empty.")

    # Extract content
    content_in_order = []
    image_dir = os.path.join(output_dir, f"{pdf_name}_images")
    os.makedirs(image_dir, exist_ok=True)

    # Process the multimodal export
    for (
        content_text,
        content_md,
        content_dt,
        page_cells,
        page_segments,
        page,
    ) in generate_multimodal_pages(conversion_result):
        # Add text content
        if content_text:
            content_in_order.append({"type": "text", "value": content_text})

        # Add table data
        if page_cells:
            for table_cells in page_cells:
                df = pd.DataFrame(table_cells)
                content_in_order.append({"type": "table", "value": df})

        # Add image data
        if page.image:
            img = Image.frombytes(
                "RGB",
                (page.image.width, page.image.height),
                page.image.tobytes(),
                "raw",
            )
            image_path = os.path.join(image_dir, f"page_{page.page_number}.png")
            img.save(image_path)
            content_in_order.append({"type": "image", "value": image_path})

    return {
        "content_in_order": content_in_order,
        "image_dir": image_dir,
    }
