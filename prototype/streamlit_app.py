# import streamlit as st
# st.set_page_config(
#     page_title="DataNexus Pro",
#     page_icon="📊",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )
 
# import io
# import base64
# import tempfile
# from pathlib import Path
# import os
# import sys
# import requests
# import shutil
 
# # Add project root to Python path
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
# sys.path.insert(0, project_root)
# API_EN_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
# API_OP_URL = os.getenv('API_BASE_URL', 'http://localhost:8001')
 
# # Initialize session state
# if 'extracted_content' not in st.session_state:
#     st.session_state.extracted_content = ""
# if 'extraction_metadata' not in st.session_state:
#     st.session_state.extraction_metadata = {}
# API_EN_URL = os.getenv('API_EN_URL', 'http://localhost:8000')
# API_OP_URL = os.getenv('API_OP_URL', 'http://localhost:8001')

# def extract_pdf_text(uploaded_file, extraction_type="enterprise"):
#     """Extract text from PDF using either enterprise or opensource solution"""
#     pdf_path = None
#     try:
#         # Create temporary file and directory
#         with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
#             tmp_file.write(uploaded_file.getvalue())
#             pdf_path = Path(tmp_file.name)
        
#         output_dir = Path("temp_output") / "pdf_extraction"
#         output_dir.mkdir(parents=True, exist_ok=True)
        
#         if extraction_type == "enterprise":
#             # Enterprise PDF extraction using API
#             response = requests.post(
#                 f"{API_EN_URL}/extract-pdf/enterprise",
#                 json={
#                     "pdf_path": str(pdf_path),
#                     "output_dir": str(output_dir)
#                 }
#             )
#             result = requests.post(
#                 f"{API_EN_URL}/process-zip/enterprise",
#                 json={
#                     "zip_path": response.json().get("zip_path")
                    
#                 }
#             )   
#             if result.status_code != 200:
#                 st.error(f"PDF Extraction API Error: {response.json().get('detail', 'Unknown error')}")
#                 return None

#             result_data = result.json()
#             markdown_url = result_data["output_locations"]["markdown_file"]
#             if result_data["status"] == "success":
#                 markdown_response = requests.get(markdown_url)
#                 if markdown_response.status_code == 200:
#                     content = markdown_response.text
#                     st.session_state.extraction_metadata = {
#                         "markdown_file": markdown_url,
#                         "images_directory": result_data["output_locations"].get("base_path"),
#                         "bucket": result_data["output_locations"].get("bucket")
#                     }
#                     return content
#                 else:
#                     st.error("Markdown file not found")
#                     return None
#         else:
#             # Open source PDF extraction
#             files = {'file': ('uploaded.pdf', uploaded_file.getvalue(), 'application/pdf')}
#             response = requests.post(
#                 f"{API_OP_URL}/pdf-process/opensource",
#                 files=files
#             )

#             if response.status_code != 200:
#                 st.error(f"PDF Extraction API Error: {response.json().get('detail', 'Unknown error')}")
#                 return None

#             result_data = response.json()
            
#             if result_data["status"] == "success":
#                 # Get markdown content from the URL
#                 markdown_response = requests.get(result_data["markdown_url"])
#                 if markdown_response.status_code == 200:
#                     content = markdown_response.text
#                     st.session_state.extraction_metadata = {
#                         "source_type": "pdf",
#                         "markdown_url": result_data["markdown_url"],
#                         "table_count": result_data.get("table_count", 0),
#                         "image_count": result_data.get("image_count", 0),
#                         "status": "success"
#                     }
#                     return content
#                 else:
#                     st.error("Failed to fetch markdown content")
#                     return None

#     except Exception as e:
#         st.error(f"Error processing PDF: {str(e)}")
#         return None
    
#     finally:
#         # Cleanup temporary files
#         if pdf_path and pdf_path.exists():
#             try:
#                 pdf_path.unlink()
#             except Exception as e:
#                 print(f"Error removing temporary file: {e}")
 
# def scrape_website(url, scraping_type="enterprise"):
#     """Scrape content from website using either enterprise or opensource solution"""
#     try:
#         output_dir = Path("temp_output") / "web_scraping"
#         output_dir.mkdir(parents=True, exist_ok=True)
        
#         if scraping_type == "enterprise":
#             # Enterprise web scraping using API
#             response = requests.post(
#                 f"{API_EN_URL}/web-scraping/enterprise",
#                 json={
#                     "url": url,
#                     "output_dir": str(output_dir)
#                 }
#             )

        
#             if response.status_code != 200:
#                 st.error(f"Web Scraping API Error: {response.json().get('detail', 'Unknown error')}")
#                 return None

#             result = requests.post(
#                 f"{API_EN_URL}/web-process/",
#                 json={
#                     "md_path": response.json().get("saved_path"),
                   
#                 }
#             )
            
           
#             result_data = result.json()
            
#             markdown_url = result_data.get("saved_path")
           
            
#             if result_data["status"] == "success":
#                 markdown_response = requests.get(markdown_url)
#                 print(markdown_response.text)
#                 content = markdown_response.text
#                 # print(f"Content length: {len(content)}")
#                 # print(f"First 100 characters: {content[:100]}")
#                 st.session_state.extraction_metadata = {
#                     "markdown_file": markdown_url
#                 }
#                 print(f"Content length is the : {len(content)}")
#                 print(f"First 100 characters: {content[:100]}")
#                 return content
               
#         else:
#             # Open source web scraping using API
#             response = requests.post(
#                 f"{API_OP_URL}/web-scraping/opensource",
#                 json={
#                     "url": url,
#                 }
#             )
#             print("This is the response",response.json)
#             result = requests.post(
#                 f"{API_OP_URL}/web-process/opensource",
#                 json={
#                     "url": response.json().get("saved_path"),
#                 }
#             )
#             if result.status_code != 200:
#                 st.error(f"Web Scraping API Error: {response.json().get('detail', 'Unknown error')}")
#                 return None

#             result_data = result.json()
#             markdown_url = result_data.get("saved_path")
#             print("This is the markdown url",markdown_url)
#             print("This is from the Result data",result_data)
#             if result_data["status"] == "success":
#                 markdown_response = requests.get(markdown_url)
#                 print(markdown_response.text)
#                 content = markdown_response.text
#                     # markdown_response = requests.get(result_data["output_locations"]["markdown_file"])
#                 st.session_state.extraction_metadata = {
#                             "markdown_file": markdown_url,
#                 }
#                 return content
              

#     except Exception as e:
#         st.error(f"Error scraping website: {str(e)}")
#         return None
    
#     finally:
#         # Cleanup temporary files
#         try:
#             if output_dir.exists():
#                 shutil.rmtree(output_dir)
#         except Exception as e:
#             print(f"Error cleaning up temporary files: {e}")

# def get_download_link(text, filename="extracted_content.md"):
#     """Create download link for extracted content"""
#     try:
#         b64 = base64.b64encode(text.encode()).decode()
#         return f'<a href="data:text/markdown;base64,{b64}" download="{filename}" class="download-button">Download Markdown File</a>'
#     except Exception as e:
#         st.error(f"Error creating download link: {str(e)}")
#         return None
    
# # Main layout
# st.title("📊 DataNexus Pro")
# st.subheader("Unified Data Extraction Platform")
 
# # Sidebar
# with st.sidebar:
#     st.header("Dashboard Controls")
#     extraction_type = st.selectbox(
#         "Select Extraction Type",
#         ["PDF Extraction", "Web Scraping"]
#     )
 
#     extraction_engine = st.radio(
#         "Select Engine",
#         ["Enterprise (Advanced)", "Open Source (Basic)"]
#     )
 
# # Main content tabs
# tab1, tab2, tab3 = st.tabs(["📥 Data Source", "📄 Content", "📊 Analysis"])
 
# with tab1:
#     st.header("Data Source/Extraction")
 
#     if extraction_type == "PDF Extraction":
#         uploaded_file = st.file_uploader("Upload PDF file", type=['pdf'])
 
#         if uploaded_file is not None and st.button("🚀 Extract Content"):
#             with st.spinner("Processing PDF..."):
#                 engine = "enterprise" if "Enterprise" in extraction_engine else "opensource"
#                 st.session_state.extracted_content = extract_pdf_text(uploaded_file, engine)
#                 if st.session_state.extracted_content:
#                     st.success("✅ PDF extracted successfully!")
 
#     else:  # Web Scraping
#         url = st.text_input("Enter website URL")
#         if url and st.button("🌐 Scrape Content"):
#             with st.spinner("Scraping website..."):
#                 engine = "enterprise" if "Enterprise" in extraction_engine else "opensource"
#                 st.session_state.extracted_content = scrape_website(url, engine)
#                 if st.session_state.extracted_content:
#                     st.success("✅ Website scraped successfully!")
 
# with tab2:
#     st.header("Extracted Content")
#     if st.session_state.extracted_content:
#         st.markdown(st.session_state.extracted_content)
#         st.markdown(get_download_link(st.session_state.extracted_content), unsafe_allow_html=True)
        
#         if st.session_state.extraction_metadata:
#             st.subheader("📊 Extraction Details")
#             if st.session_state.extraction_metadata.get("source_type") == "pdf":
#                 col1, col2 = st.columns(2)
#                 with col1:
#                     st.metric("📑 Tables", st.session_state.extraction_metadata.get('tables', 0))
#                 with col2:
#                     st.metric("🖼️ Images", st.session_state.extraction_metadata.get('images', 0))
#             elif st.session_state.extraction_metadata.get("source_type") == "web":
#                 st.text(f"Source URL: {st.session_state.extraction_metadata.get('source_url', 'N/A')}")
#     else:
#         st.info("💡 No content extracted yet. Please use the Data Source tab to extract content.")
 
# with tab3:
#     st.header("Analysis Dashboard")
#     if st.session_state.extracted_content:
#         # Text analysis
#         word_count = len(st.session_state.extracted_content.split())
#         char_count = len(st.session_state.extracted_content)
        
#         # Display metrics
#         col1, col2, col3 = st.columns(3)
#         with col1:
#             st.metric("📝 Word Count", word_count)
#         with col2:
#             st.metric("📊 Character Count", char_count)
#         with col3:
#             avg_word_length = round(char_count / word_count, 2) if word_count > 0 else 0
#             st.metric("📏 Avg Word Length", avg_word_length)
        
#         # Content preview
#         st.subheader("📄 Content Preview")
#         with st.expander("Show first 500 characters"):
#             st.text_area(
#                 "Content sample",
#                 st.session_state.extracted_content[:500],
#                 height=200,
#                 disabled=True
#             )
#     else:
#         st.info("💡 No content to analyze. Please extract content first.")
 
# # Styling
# st.markdown("""
#    <style>
#     /* Global styles */
#     .stApp {
#         background-color: white;
#     }
    
#     /* Sidebar styling */
#     [data-testid="stSidebar"] {
#         background-color: white;
#     }
    
#     /* Navigation items in sidebar */
#     .css-17lntkn {
#         color: #A9A9A9 !important;
#         font-weight: normal;
#     }
    
#     /* Selected navigation item */
#     .css-17lntkn.selected {
#         background-color: rgba(240, 242, 246, 0.5) !important;
#         border-radius: 4px;
#     }
    
#     /* Main content text */
#     h1, h2, h3, p {
#         color: black !important;
#     }
    
#     /* Feature cards */
#     .feature-card {
#         background-color: #f8f9fa;
#         border-radius: 8px;
#         padding: 20px;
#         margin: 10px 0;
#         border: 1px solid #eee;
#     }
    
#     .feature-card h3 {
#         color: black !important;
#         margin-bottom: 10px;
#     }
    
#     .feature-card p {
#         color: #666 !important;
#     }
    
#     /* Stats container */
#     .stats-container {
#         background-color: #f8f9fa;
#         border-radius: 8px;
#         padding: 20px;
#         margin: 20px 0;
#         border: 1px solid #eee;
#     }
    
#     /* Metric styling */
#     [data-testid="stMetricValue"] {
#         color: black !important;
#     }
    
#     /* Button styling */
#     .stButton > button {
#         background-color: white;
#         color: black;
#         border: 1px solid #ddd;
#         border-radius: 4px;
#         padding: 0.5rem 1.5rem;
#         width: 100%;
#     }
    
#     .stButton > button:hover {
#         background-color: #f8f9fa;
#         border-color: #ddd;
#     }
 
#     /* Make header white */
#     header[data-testid="stHeader"] {
#         background-color: white;
#     }
    
#     /* Remove any dark backgrounds */
#     .stApp header {
#         background-color: white !important;
#     }
    
#     /* Style header elements */
#     .stApp header button {
#         color: black !important;
#     }
    
#     /* Sidebar navigation styling */
#     [data-testid="stSidebar"] {
#         background-color: white;
#     }
    
#     /* Remove "data extraction" from top navigation */
#     .css-17lntkn[aria-label="data extraction"] {
#         display: none !important;
#     }
    
#     /* Navigation items in sidebar */
#     .css-17lntkn {
#         color: #A9A9A9 !important;
#         font-weight: normal;
#     }
    
 
#     /* Fix for the uploaded file name color in the file uploader */
# [data-testid="stFileUploader"] div {
#     color: black !important; /* Ensure the file name is visible */
#     font-weight: 500;        /* Adjust font weight as needed */
# }
 
# /* Adjust the input and dropdown text color */
# .stTextInput, .stSelectbox {
#     color: black !important;
#     background-color: white !important;
# }
 
 
 
 
# /* Ensure that all text within the sidebar is visible */
# [data-testid="stSidebar"] * {
#     color: black !important;
# }
 
# /* General fix for button and interactive element text */
# .stButton > button, .stRadio > div, .stSelectbox > div {
#     color: black !important;
#     background-color: white !important;
# }
 
# /* Specific styling for the file uploader */
# .stFileUploader {
#     background-color: #f8f9fa;  /* Light background for better visibility */
#     border: 1px solid #ddd;      /* Light border */
#     border-radius: 4px;
# }
 
 
#     /* Quick Navigation buttons */
#     .stButton > button {
#         background-color: transparent;
#         color: black;
#         border: none;
#         text-align: left;
#         padding: 8px 0;
#         font-weight: normal;
#     }
    
#     .stButton > button:hover {
#         background-color: rgba(240, 242, 246, 0.5);
#         border-radius: 4px;
#     }
#     </style>
    
# """, unsafe_allow_html=True)