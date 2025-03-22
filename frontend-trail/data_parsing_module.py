import streamlit as st
import io
import base64
import tempfile
from pathlib import Path
import os
import sys
import requests
import shutil

def show_data_parsing():
    """Display the data parsing page content"""
    
    # Apply data parsing specific styling
    st.markdown("""
        <style>
        /* Stats container */
        .stats-container {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            border: 1px solid #eee;
        }
        
        /* Button styling */
        .stButton > button {
            background-color: white;
            color: black;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 0.5rem 1.5rem;
            width: 100%;
        }
        
        .stButton > button:hover {
            background-color: #f8f9fa;
            border-color: #ddd;
        }
        
        /* Navigation highlight */
        .nav-highlight {
            background-color: #4b8bf5;
            color: white !important;
            border-radius: 4px;
            padding: 8px 12px;
        }
        .nav-highlight:hover {
            background-color: #3a7ae0;
        }
        
        /* Download button */
        .download-button {
            display: inline-block;
            background-color: #4CAF50;
            color: white;
            padding: 8px 16px;
            text-decoration: none;
            border-radius: 4px;
            margin-top: 10px;
        }
        .download-button:hover {
            background-color: #45a049;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Environment variables
    API_EN_URL = os.getenv('API_EN_URL', 'http://localhost:8000')
    API_OP_URL = os.getenv('API_OP_URL', 'http://localhost:8001')
    
    # Initialize session state if not already initialized
    if 'extracted_content' not in st.session_state:
        st.session_state.extracted_content = ""
    if 'extraction_metadata' not in st.session_state:
        st.session_state.extraction_metadata = {}
    if 'parsed_documents' not in st.session_state:
        st.session_state.parsed_documents = {}
    
    # Main layout
    st.title("📄 Data Parsing")
    st.subheader("Extract Content from PDFs and Websites")
    
    # Sidebar content specific to data parsing
    with st.sidebar:
        st.markdown("### Dashboard Controls")
        extraction_type = st.selectbox(
            "Select Extraction Type",
            ["PDF Extraction", "Web Scraping"]
        )
    
        extraction_engine = st.radio(
            "Select Engine",
            ["Enterprise (Advanced)", "Open Source (Basic)"]
        )
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["📥 Data Source", "📄 Content", "📊 Analysis"])
    
    with tab1:
        st.header("Data Source/Extraction")
    
        if extraction_type == "PDF Extraction":
            uploaded_file = st.file_uploader("Upload PDF file", type=['pdf'])
    
            if uploaded_file is not None and st.button("🚀 Extract Content", type="primary"):
                with st.spinner("Processing PDF..."):
                    engine = "enterprise" if "Enterprise" in extraction_engine else "opensource"
                    st.session_state.extracted_content = extract_pdf_text(uploaded_file, engine)
                    if st.session_state.extracted_content:
                        st.success("✅ PDF extracted successfully!")
                        # Save to session state for use in AI chat
                        if 'parsed_documents' not in st.session_state:
                            st.session_state.parsed_documents = {}
                        st.session_state.parsed_documents[uploaded_file.name] = {
                            "content": st.session_state.extracted_content,
                            "metadata": st.session_state.extraction_metadata,
                            "type": "pdf",
                            "extraction_engine": engine
                        }
    
        else:  # Web Scraping
            url = st.text_input("Enter website URL")
            if url and st.button("🌐 Scrape Content", type="primary"):
                with st.spinner("Scraping website..."):
                    engine = "enterprise" if "Enterprise" in extraction_engine else "opensource"
                    st.session_state.extracted_content = scrape_website(url, engine)
                    if st.session_state.extracted_content:
                        st.success("✅ Website scraped successfully!")
                        # Save to session state for use in AI chat
                        if 'parsed_documents' not in st.session_state:
                            st.session_state.parsed_documents = {}
                        st.session_state.parsed_documents[url] = {
                            "content": st.session_state.extracted_content,
                            "metadata": st.session_state.extraction_metadata,
                            "type": "web",
                            "extraction_engine": engine
                        }
    
    with tab2:
        st.header("Extracted Content")
        if st.session_state.extracted_content:
            st.markdown(st.session_state.extracted_content)
            st.markdown(get_download_link(st.session_state.extracted_content), unsafe_allow_html=True)
            
            if st.session_state.extraction_metadata:
                st.subheader("📊 Extraction Details")
                if st.session_state.extraction_metadata.get("source_type") == "pdf":
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("📑 Tables", st.session_state.extraction_metadata.get('tables', 0))
                    with col2:
                        st.metric("🖼️ Images", st.session_state.extraction_metadata.get('images', 0))
                elif st.session_state.extraction_metadata.get("source_type") == "web":
                    st.text(f"Source URL: {st.session_state.extraction_metadata.get('source_url', 'N/A')}")
        else:
            st.info("💡 No content extracted yet. Please use the Data Source tab to extract content.")
    
    with tab3:
        st.header("Analysis Dashboard")
        if st.session_state.extracted_content:
            # Text analysis
            word_count = len(st.session_state.extracted_content.split())
            char_count = len(st.session_state.extracted_content)
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📝 Word Count", word_count)
            with col2:
                st.metric("📊 Character Count", char_count)
            with col3:
                avg_word_length = round(char_count / word_count, 2) if word_count > 0 else 0
                st.metric("📏 Avg Word Length", avg_word_length)
            
            # Content preview
            st.subheader("📄 Content Preview")
            with st.expander("Show first 500 characters"):
                st.text_area(
                    "Content sample",
                    st.session_state.extracted_content[:500],
                    height=200,
                    disabled=True
                )
                
            # Add a button to go to AI Chat with this document
            st.markdown("### Continue with AI Analysis")
            if st.button("🤖 Chat with AI about this document", type="primary"):
                # Store the last processed document as the active one for chat
                if 'active_document' not in st.session_state:
                    st.session_state.active_document = {}
                    
                if extraction_type == "PDF Extraction" and uploaded_file is not None:
                    st.session_state.active_document = {
                        "name": uploaded_file.name,
                        "content": st.session_state.extracted_content,
                        "type": "pdf"
                    }
                elif extraction_type == "Web Scraping" and url:
                    st.session_state.active_document = {
                        "name": url,
                        "content": st.session_state.extracted_content,
                        "type": "web"
                    }
                
                # Navigate to the chat page
                st.session_state.current_page = "chat_ai"
                st.rerun()

def extract_pdf_text(uploaded_file, extraction_type="enterprise"):
    """Extract text from PDF using either enterprise or opensource solution"""
    API_EN_URL = os.getenv('API_EN_URL', 'http://localhost:8000')
    API_OP_URL = os.getenv('API_OP_URL', 'http://localhost:8001')
    
    pdf_path = None
    try:
        # Create temporary file and directory
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            pdf_path = Path(tmp_file.name)
        
        output_dir = Path("temp_output") / "pdf_extraction"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if extraction_type == "enterprise":
            # Enterprise PDF extraction using API
            response = requests.post(
                f"{API_EN_URL}/extract-pdf/enterprise",
                json={
                    "pdf_path": str(pdf_path),
                    "output_dir": str(output_dir)
                }
            )
            result = requests.post(
                f"{API_EN_URL}/process-zip/enterprise",
                json={
                    "zip_path": response.json().get("zip_path")
                    
                }
            )   
            if result.status_code != 200:
                st.error(f"PDF Extraction API Error: {response.json().get('detail', 'Unknown error')}")
                return None

            result_data = result.json()
            markdown_url = result_data["output_locations"]["markdown_file"]
            if result_data["status"] == "success":
                markdown_response = requests.get(markdown_url)
                if markdown_response.status_code == 200:
                    content = markdown_response.text
                    st.session_state.extraction_metadata = {
                        "markdown_file": markdown_url,
                        "images_directory": result_data["output_locations"].get("base_path"),
                        "bucket": result_data["output_locations"].get("bucket")
                    }
                    return content
                else:
                    st.error("Markdown file not found")
                    return None
        else:
            # Open source PDF extraction
            files = {'file': ('uploaded.pdf', uploaded_file.getvalue(), 'application/pdf')}
            response = requests.post(
                f"{API_OP_URL}/pdf-process/opensource",
                files=files
            )

            if response.status_code != 200:
                st.error(f"PDF Extraction API Error: {response.json().get('detail', 'Unknown error')}")
                return None

            result_data = response.json()
            
            if result_data["status"] == "success":
                # Get markdown content from the URL
                markdown_response = requests.get(result_data["markdown_url"])
                if markdown_response.status_code == 200:
                    content = markdown_response.text
                    st.session_state.extraction_metadata = {
                        "source_type": "pdf",
                        "markdown_url": result_data["markdown_url"],
                        "table_count": result_data.get("table_count", 0),
                        "image_count": result_data.get("image_count", 0),
                        "status": "success"
                    }
                    return content
                else:
                    st.error("Failed to fetch markdown content")
                    return None

    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return None
    
    finally:
        # Cleanup temporary files
        if pdf_path and pdf_path.exists():
            try:
                pdf_path.unlink()
            except Exception as e:
                print(f"Error removing temporary file: {e}")

def scrape_website(url, scraping_type="enterprise"):
    """Scrape content from website using either enterprise or opensource solution"""
    API_EN_URL = os.getenv('API_EN_URL', 'http://localhost:8000')
    API_OP_URL = os.getenv('API_OP_URL', 'http://localhost:8001')
    
    try:
        output_dir = Path("temp_output") / "web_scraping"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if scraping_type == "enterprise":
            # Enterprise web scraping using API
            response = requests.post(
                f"{API_EN_URL}/web-scraping/enterprise",
                json={
                    "url": url,
                    "output_dir": str(output_dir)
                }
            )

        
            if response.status_code != 200:
                st.error(f"Web Scraping API Error: {response.json().get('detail', 'Unknown error')}")
                return None

            result = requests.post(
                f"{API_EN_URL}/web-process/",
                json={
                    "md_path": response.json().get("saved_path"),
                   
                }
            )
            
           
            result_data = result.json()
            
            markdown_url = result_data.get("saved_path")
           
            
            if result_data["status"] == "success":
                markdown_response = requests.get(markdown_url)
                content = markdown_response.text
                st.session_state.extraction_metadata = {
                    "markdown_file": markdown_url
                }
                return content
               
        else:
            # Open source web scraping using API
            response = requests.post(
                f"{API_OP_URL}/web-scraping/opensource",
                json={
                    "url": url,
                }
            )
            result = requests.post(
                f"{API_OP_URL}/web-process/opensource",
                json={
                    "url": response.json().get("saved_path"),
                }
            )
            if result.status_code != 200:
                st.error(f"Web Scraping API Error: {response.json().get('detail', 'Unknown error')}")
                return None

            result_data = result.json()
            markdown_url = result_data.get("saved_path")
            if result_data["status"] == "success":
                markdown_response = requests.get(markdown_url)
                content = markdown_response.text
                st.session_state.extraction_metadata = {
                    "markdown_file": markdown_url,
                }
                return content
              

    except Exception as e:
        st.error(f"Error scraping website: {str(e)}")
        return None
    
    finally:
        # Cleanup temporary files
        try:
            if output_dir.exists():
                shutil.rmtree(output_dir)
        except Exception as e:
            print(f"Error cleaning up temporary files: {e}")

def get_download_link(text, filename="extracted_content.md"):
    """Create download link for extracted content"""
    try:
        b64 = base64.b64encode(text.encode()).decode()
        return f'<a href="data:text/markdown;base64,{b64}" download="{filename}" class="download-button">Download Markdown File</a>'
    except Exception as e:
        st.error(f"Error creating download link: {str(e)}")
        return None