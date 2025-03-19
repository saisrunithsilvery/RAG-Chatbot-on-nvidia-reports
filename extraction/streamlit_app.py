import streamlit as st
import tempfile
from pathlib import Path
import asyncio
from docling_converter import DoclingConverter  # Ensure this is correctly imported
from PIL import Image

# Fix asyncio event loop issue
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# Initialize converter
docling_converter = DoclingConverter()

st.title("PDF to Markdown Converter")
st.markdown("Upload a PDF file, and this tool will convert it into markdown with extracted images and tables.")

# File uploader
uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])

if uploaded_file:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        pdf_path = temp_dir_path / uploaded_file.name
        output_dir = temp_dir_path / "output"

        # Save the uploaded file
        with open(pdf_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.info("Processing PDF... Please wait.")

        try:
            result = docling_converter.process_pdf(pdf_path, output_dir)

            if result["status"] == "success":
                st.success("Conversion successful!")

                # Show Markdown preview
                markdown_path = result["markdown_path"]
                if markdown_path.exists():
                    with open(markdown_path, "r", encoding="utf-8") as md_file:
                        markdown_content = md_file.read()
                        st.subheader("Extracted Markdown")
                        st.code(markdown_content, language="markdown")
                        st.text_area("Full Extracted Content", markdown_content, height=400)

                # Show extracted images
                st.subheader("Extracted Images")
                images_dir = output_dir / "images"
                image_files = list(images_dir.glob("*.png"))

                if image_files:
                    for img_file in image_files:
                        st.image(Image.open(img_file), caption=img_file.name, use_container_width=True)
                else:
                    st.info("No images extracted from the document.")

            elif result["status"] == "partial_success":
                st.warning(f"Partial conversion: {result['message']}")
            else:
                st.error(f"Error: {result['message']}")

        except RuntimeError as e:
            st.error(f"Runtime Error: {str(e)}")


# import streamlit as st
# import tempfile
# from pathlib import Path
# from docling_converter import DoclingConverter 
# from PIL import Image

# # Initialize converter
# docling_converter = DoclingConverter()

# st.title("PDF to Markdown Converter")
# st.markdown("Upload a PDF file, and this tool will convert it into markdown with extracted images and tables.")

# # File uploader
# uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])

# if uploaded_file:
#     with tempfile.TemporaryDirectory() as temp_dir:
#         temp_dir_path = Path(temp_dir)
#         pdf_path = temp_dir_path / uploaded_file.name
#         output_dir = temp_dir_path / "output"
        
#         # Save the uploaded file
#         with open(pdf_path, "wb") as f:
#             f.write(uploaded_file.getbuffer())
        
#         st.info("Processing PDF... Please wait.")
#         result = docling_converter.process_pdf(pdf_path, output_dir)
        
#         if result["status"] == "success":
#             st.success("Conversion successful!")
            
#             # Show Markdown preview
#             markdown_path = result["markdown_path"]
#             if markdown_path.exists():
#                 with open(markdown_path, "r", encoding="utf-8") as md_file:
#                     markdown_content = md_file.read()
#                     st.subheader("Extracted Markdown")
#                     st.code(markdown_content, language="markdown")
#                     st.text_area("Full Extracted Content", markdown_content, height=400)
            
#             # Show extracted images
#             st.subheader("Extracted Images")
#             images_dir = output_dir / "images"
#             image_files = list(images_dir.glob("*.png"))
            
#             if image_files:
#                 for img_file in image_files:
#                     st.image(Image.open(img_file), caption=img_file.name, use_container_width=True)
#             else:
#                 st.info("No images extracted from the document.")
        
#         elif result["status"] == "partial_success":
#             st.warning(f"Partial conversion: {result['message']}")
#         else:
#             st.error(f"Error: {result['message']}")