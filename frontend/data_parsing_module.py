import streamlit as st
import io
import base64
import os
import requests
import json
import re
from datetime import datetime

def show_data_parsing():
    """Display the data parsing page with RAG pipeline integration"""
    
    # Apply styling
    st.markdown("""
        <style>
        .stats-container {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            border: 1px solid #eee;
        }
        
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
        
        .nav-highlight {
            background-color: #4b8bf5;
            color: white !important;
            border-radius: 4px;
            padding: 8px 12px;
        }
        
        .download-button {
            display: inline-block;
            background-color: #4CAF50;
            color: white;
            padding: 8px 16px;
            text-decoration: none;
            border-radius: 4px;
            margin-top: 10px;
        }
        
        .rag-container {
            background-color: #f1f8ff;
            border-radius: 8px;
            padding: 15px;
            margin: 15px 0;
            border: 1px solid #cce5ff;
        }
        
        .document-list {
            max-height: 600px;
            overflow-y: auto;
            padding-right: 10px;
        }
        
        .document-item {
            padding: 8px 12px;
            border-radius: 4px;
            margin: 5px 0;
            cursor: pointer;
            border-left: 3px solid transparent;
            transition: all 0.2s;
        }
        
        .document-item:hover {
            background-color: #f1f8ff;
            border-left: 3px solid #4b8bf5;
        }
        
        .document-item.active {
            background-color: #e1efff;
            border-left: 3px solid #4b8bf5;
            font-weight: 500;
        }
        
        .file-tag {
            display: inline-block;
            background-color: #e9ecef;
            padding: 2px 8px;
            border-radius: 12px;
            margin-right: 5px;
            font-size: 0.8em;
        }
        
        .file-tag.pdf {
            background-color: #ffeeba;
            color: #856404;
        }
        
        .file-tag.q1 {
            background-color: #d4edda;
            color: #155724;
        }
        
        .file-tag.q2 {
            background-color: #d1ecf1;
            color: #0c5460;
        }
        
        .file-tag.q3 {
            background-color: #f8d7da;
            color: #721c24;
        }
        
        .file-tag.q4 {
            background-color: #e2e3e5;
            color: #383d41;
        }
        
        .search-box {
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 8px;
            margin-bottom: 15px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Environment variables
    API_EN_URL = os.getenv('API_EN_URL', 'http://localhost:8000')
    API_OP_URL = os.getenv('API_OP_URL', 'http://localhost:8001')
    
    # Initialize session state
    init_session_state()
    
    # Main layout
    st.title("📄 Data Parsing & RAG Pipeline")
    st.subheader("Extract Content and Configure RAG Pipeline")
    
    # Sidebar configuration
    configure_sidebar()
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📥 Data Source", "📄 Content", "🔍 RAG Pipeline", "📊 Analysis"])
    
    with tab1:
        display_data_source_tab(API_EN_URL, API_OP_URL)
    
    with tab2:
        display_content_tab()
    
    with tab3:
        display_rag_pipeline_tab(API_EN_URL)
    
    with tab4:
        display_analysis_tab()

def init_session_state():
    """Initialize session state variables if not already set"""
    if 'extracted_content' not in st.session_state:
        st.session_state.extracted_content = ""
    if 'extraction_metadata' not in st.session_state:
        st.session_state.extraction_metadata = {}
    if 'parsed_documents' not in st.session_state:
        st.session_state.parsed_documents = {}
    if 'rag_config' not in st.session_state:
        st.session_state.rag_config = {
            "vector_db": "faiss",
            "chunking_strategy": "recursive",
            "chunk_size": 500,
            "chunk_overlap": 10
        }
    if 'available_documents' not in st.session_state:
        st.session_state.available_documents = {}
    if 'selected_document' not in st.session_state:
        st.session_state.selected_document = None
    if 's3_files' not in st.session_state:
        st.session_state.s3_files = []

def configure_sidebar():
    """Configure the sidebar options"""
    with st.sidebar:
        st.markdown("### Source Configuration")
        extraction_type = st.selectbox(
            "Select Source Type",
            ["PDF Upload", "Web Scrape", "S3 RAW Reports"]
        )
        
        # Store the selected extraction type
        st.session_state.extraction_type = extraction_type
        
        # Show parser options based on extraction type
        if extraction_type == "PDF Upload":
            extraction_engine = st.radio(
                "Select Parser Type",
                ["docling", "mistral_ai", "adobe", "opensource"]
            )
        else:
            extraction_engine = st.radio(
                "Select Engine",
                ["Enterprise", "Open Source"]
            )
        
        # Store the selected engine
        st.session_state.extraction_engine = extraction_engine
        
        # RAG configuration
        st.markdown("### RAG Pipeline Options")
        
        vector_db = st.selectbox(
            "Vector Database",
            ["faiss", "chromadb", "pinecone"],
            index=["faiss", "chromadb", "pinecone"].index(st.session_state.rag_config.get("vector_db", "faiss"))
        )
        
        chunking_strategy = st.selectbox(
            "Chunking Strategy",
            ["recursive", "character", "token"],
            index=0
        )
        
        # Update session state with RAG config
        st.session_state.rag_config["vector_db"] = vector_db
        st.session_state.rag_config["chunking_strategy"] = chunking_strategy

def display_data_source_tab(API_EN_URL, API_OP_URL):
    """Display the Data Source tab content"""
    st.header("Data Source")
    
    extraction_type = st.session_state.get("extraction_type", "PDF Upload")
    extraction_engine = st.session_state.get("extraction_engine", "docling")
    
    if extraction_type == "PDF Upload":
        uploaded_file = st.file_uploader("Upload PDF file", type=['pdf'])

        if uploaded_file is not None and st.button("🚀 Extract Content", type="primary"):
            with st.spinner("Processing PDF..."):
                # Pass parser type directly from UI selection
                parsetype = extraction_engine
                
                # Get chunking strategy and vector database from RAG config
                chunking_strategy = st.session_state.rag_config.get("chunking_strategy", "recursive")
                vectordb = st.session_state.rag_config.get("vector_db", "faiss")
                
                st.session_state.extracted_content = extract_pdf_text(
                    API_EN_URL, 
                    uploaded_file,
                    parsetype,
                    chunking_strategy,
                    vectordb
                )
                
                if st.session_state.extracted_content:
                    st.success("✅ PDF extracted successfully!")
                    store_document(uploaded_file.name, "pdf", parsetype)
    
    elif extraction_type == "Web Scrape":
        url = st.text_input("Enter website URL")
        if url and st.button("🌐 Scrape Content", type="primary"):
            with st.spinner("Scraping website..."):
                engine = "enterprise" if extraction_engine == "Enterprise" else "opensource"
                st.session_state.extracted_content = scrape_website(API_EN_URL, API_OP_URL, url, engine)
                if st.session_state.extracted_content:
                    st.success("✅ Website scraped successfully!")
                    store_document(url, "web", engine)
    
    else:  # S3 RAW Reports
        st.subheader("NVIDIA Reports from S3")
        
        # Load available documents from S3
        if not st.session_state.s3_files:
            try:
                with st.spinner("Loading NVIDIA reports from S3..."):
                    response = requests.get(f"{API_EN_URL}/files")
                    if response.status_code == 200:
                        files_data = response.json().get("files", [])
                        # Filter out empty entries and sort by filename
                        st.session_state.s3_files = [
                            file for file in files_data 
                            if file.get("filename") and file.get("file_url")
                        ]
                        # Sort files by year and quarter
                        st.session_state.s3_files.sort(
                            key=lambda x: (
                                # Extract year from filename (default to 0 if not found)
                                int(re.search(r'q\d-(\d{4})', x.get("filename", "").lower()).group(1) 
                                    if re.search(r'q\d-(\d{4})', x.get("filename", "").lower()) else 0),
                                # Extract quarter from filename (default to 0 if not found)
                                int(re.search(r'q(\d)', x.get("filename", "").lower()).group(1) 
                                    if re.search(r'q(\d)', x.get("filename", "").lower()) else 0)
                            ),
                            reverse=True  # Most recent first
                        )
            except Exception as e:
                st.error(f"Error loading S3 documents: {str(e)}")
        
        # Create search box
        st.markdown("<div class='search-box'>", unsafe_allow_html=True)
        search_query = st.text_input("🔍 Search reports", placeholder="Enter keywords (e.g., 2023, Q1, etc.)")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Filter files based on search query
        filtered_files = st.session_state.s3_files
        if search_query:
            filtered_files = [
                file for file in st.session_state.s3_files
                if search_query.lower() in file.get("filename", "").lower()
            ]
        
        # File filters
        col1, col2 = st.columns(2)
        with col1:
            show_years = st.multiselect(
                "Filter by Year",
                sorted(set([
                    re.search(r'q\d-(\d{4})', file.get("filename", "").lower()).group(1)
                    for file in st.session_state.s3_files
                    if re.search(r'q\d-(\d{4})', file.get("filename", "").lower())
                ]), reverse=True),
                default=[]
            )
        
        with col2:
            show_quarters = st.multiselect(
                "Filter by Quarter",
                ["Q1", "Q2", "Q3", "Q4"],
                default=[]
            )
        
        # Apply year and quarter filters if selected
        if show_years:
            filtered_files = [
                file for file in filtered_files
                if any(year in file.get("filename", "").lower() for year in show_years)
            ]
        
        if show_quarters:
            filtered_files = [
                file for file in filtered_files
                if any(quarter.lower() in file.get("filename", "").lower() for quarter in show_quarters)
            ]
        
        # Display files in a scrollable container
        st.markdown("<div class='document-list'>", unsafe_allow_html=True)
        
        for file in filtered_files:
            filename = file.get("filename", "")
            file_url = file.get("file_url", "")
            file_size = file.get("size", 0)
            last_modified = file.get("last_modified", "")
            
            # Skip files with empty filenames
            if not filename:
                continue
            
            # Create file size display
            size_display = f"{file_size / 1024:.1f} KB" if file_size < 1024 * 1024 else f"{file_size / (1024 * 1024):.1f} MB"
            
            # Determine quarter and year for tag styling
            quarter_match = re.search(r'q(\d)', filename.lower())
            quarter = f"Q{quarter_match.group(1)}" if quarter_match else ""
            
            # Format last modified date
            try:
                last_modified_date = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
                modified_display = last_modified_date.strftime("%b %d, %Y")
            except:
                modified_display = last_modified
            
            # Determine if this file is selected
            is_active = st.session_state.selected_document == filename
            doc_class = "document-item active" if is_active else "document-item"
            
            # Create clickable document item
            doc_html = f"""
                <div class='{doc_class}' onclick="this.classList.toggle('active'); window.parent.postMessage({{
                    type: 'streamlit:setComponentValue',
                    value: '{filename}'
                }}, '*');">
                    <strong>{filename}</strong><br>
                    <span class='file-tag pdf'>PDF</span>
                    {f'<span class="file-tag {quarter.lower()}">{quarter}</span>' if quarter else ''}
                    <small style='color: #6c757d;'>{modified_display} • {size_display}</small>
                </div>
            """
            
            if st.markdown(doc_html, unsafe_allow_html=True):
                st.session_state.selected_document = filename
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Show file count
        st.markdown(f"<small>Showing {len(filtered_files)} of {len(st.session_state.s3_files)} files</small>", unsafe_allow_html=True)
        
        # Selected document actions
        if st.session_state.selected_document:
            selected_file = next((f for f in st.session_state.s3_files if f.get("filename") == st.session_state.selected_document), None)
            
            if selected_file:
                st.markdown("### Selected Document")
                st.write(f"**{selected_file.get('filename')}**")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📄 Process Document", type="primary"):
                        with st.spinner(f"Loading document: {selected_file.get('filename')}"):
                            try:
                                # Get document URL
                                doc_url = selected_file.get("file_url")
                                
                                if doc_url:
                                    # Get parser type, chunking strategy, and vector database
                                    parsetype = extraction_engine
                                    chunking_strategy = st.session_state.rag_config.get("chunking_strategy", "recursive")
                                    vectordb = st.session_state.rag_config.get("vector_db", "faiss")
                                    
                                    # Call API to process S3 PDF
                                    response = requests.post(
                                        f"{API_EN_URL}/process-s3",
                                        json={
                                            "method": "s3",
                                            "s3_url": doc_url,
                                            "parsetype": parsetype,
                                            "chunking_strategy": chunking_strategy,
                                            "vectordb": vectordb
                                        }
                                    )
                                    
                                    if response.status_code == 200:
                                        result = response.json()
                                        if result.get("status") == "success":
                                            markdown_url = result.get("markdown_url")
                                            
                                            # Fetch markdown content
                                            markdown_response = requests.get(markdown_url)
                                            if markdown_response.status_code == 200:
                                                st.session_state.extracted_content = markdown_response.text
                                                st.session_state.extraction_metadata = {
                                                    "source_type": "s3",
                                                    "file_url": doc_url,
                                                    "markdown_url": markdown_url,
                                                    "parser": parsetype,
                                                    "chunking_strategy": chunking_strategy,
                                                    "vectordb": vectordb,
                                                    "filename": selected_file.get("filename"),
                                                    "size": selected_file.get("size"),
                                                    "last_modified": selected_file.get("last_modified")
                                                }
                                                st.success(f"✅ Processed document: {selected_file.get('filename')}")
                                                store_document(selected_file.get("filename"), "s3", parsetype)
                                            else:
                                                st.error("Failed to fetch processed content")
                                        else:
                                            st.error(f"Processing Error: {result.get('message', 'Unknown error')}")
                                    else:
                                        st.error(f"API Error: {response.status_code}")
                                else:
                                    st.error("Invalid file URL")
                            except Exception as e:
                                st.error(f"Error processing document: {str(e)}")
                
                with col2:
                    if st.button("⬇️ Download Original PDF"):
                        doc_url = selected_file.get("file_url")
                        if doc_url:
                            # Create download link
                            st.markdown(f"[Download {selected_file.get('filename')}]({doc_url})", unsafe_allow_html=True)

def display_content_tab():
    """Display the Content tab"""
    st.header("Extracted Content")
    if st.session_state.extracted_content:
        st.markdown(st.session_state.extracted_content)
        st.markdown(get_download_link(st.session_state.extracted_content), unsafe_allow_html=True)
        
        if st.session_state.extraction_metadata:
            st.subheader("📊 Extraction Details")
            st.json(st.session_state.extraction_metadata)
    else:
        st.info("💡 No content extracted yet. Please use the Data Source tab to extract content.")

def display_rag_pipeline_tab(API_EN_URL):
    """Display the RAG Pipeline tab"""
    st.header("RAG Pipeline Configuration")
    
    if not st.session_state.extracted_content:
        st.warning("⚠️ Please extract or load document content first.")
    else:
        # Display current RAG configuration
        st.markdown(
            f"""
            <div class="rag-container">
            <h3>Current Configuration</h3>
            <ul>
                <li><strong>Vector Database:</strong> {st.session_state.rag_config['vector_db']}</li>
                <li><strong>Chunking Strategy:</strong> {st.session_state.rag_config['chunking_strategy']}</li>
                <li><strong>Chunk Size:</strong> {st.session_state.rag_config.get('chunk_size', 500)}</li>
                <li><strong>Chunk Overlap:</strong> {st.session_state.rag_config.get('chunk_overlap', 10)}%</li>
            </ul>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Process document button
        if st.button("⚙️ Process Document with RAG Pipeline", type="primary"):
            with st.spinner("Processing document with RAG pipeline..."):
                try:
                    # Get current document info
                    current_document = get_current_document()
                    
                    if current_document:
                        # Prepare payload for RAG processing
                        payload = {
                            "content": current_document.get("content", ""),
                            "document_name": current_document.get("name", "unknown"),
                            "document_type": current_document.get("type", "unknown"),
                            "rag_config": st.session_state.rag_config,
                            "metadata": current_document.get("metadata", {})
                        }
                        
                        # Call API to process document with RAG pipeline
                        response = requests.post(
                            f"{API_EN_URL}/rag-process",
                            json=payload
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            if result.get("status") == "success":
                                st.success("✅ Document processed successfully with RAG pipeline!")
                                
                                # Add RAG processing results to session state
                                st.session_state.rag_results = result.get("results", {})
                                
                                # Display metrics
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Chunks Created", result.get("chunk_count", 0))
                                with col2:
                                    st.metric("Indexed Vectors", result.get("vector_count", 0))
                                with col3:
                                    st.metric("Processing Time", f"{result.get('processing_time', 0):.2f}s")
                            else:
                                st.error(f"RAG Processing Error: {result.get('message', 'Unknown error')}")
                        else:
                            st.error(f"API Error: {response.status_code}")
                except Exception as e:
                    st.error(f"Error processing document with RAG: {str(e)}")
        
        # If results are available, show them
        if 'rag_results' in st.session_state and st.session_state.rag_results:
            with st.expander("View RAG Processing Results"):
                st.json(st.session_state.rag_results)

def display_analysis_tab():
    """Display the Analysis tab"""
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
            current_document = get_current_document()
            if current_document:
                if 'active_document' not in st.session_state:
                    st.session_state.active_document = {}
                
                st.session_state.active_document = current_document
                
                # Navigate to the chat page (if implemented)
                st.session_state.current_page = "chat_ai"
                st.rerun()
    else:
        st.info("💡 No content extracted yet. Please extract or load content first.")

def extract_pdf_text(api_url, uploaded_file, parsetype="docling", chunking_strategy="recursive", vectordb="faiss"):
    """Extract text from PDF using the specified parser"""
    PDF_UPLOAD_ENDPOINT = "/upload"
    
    try:
        # Prepare file for upload
        files = {'file': (uploaded_file.name, uploaded_file.getvalue(), 'application/pdf')}
        
        # Prepare form data with parser information
        form_data = {
            "method": "upload",
            "parsetype": parsetype,
            "chunking_strategy": chunking_strategy,
            "vectordb": vectordb
        }
        
        request_data = json.dumps(form_data)
        
        # Upload file to API
        response = requests.post(
            f"{api_url}{PDF_UPLOAD_ENDPOINT}",
            files=files,
            data={"request_data": request_data}
        )
        print(response.json())
        if response.status_code != 201:
            st.error(f"PDF Upload Error: {response.json().get('detail', 'Unknown error')}")
            return None
        
        result_data = response.json()
        
        if result_data.get("status") == "success":
            # Get markdown URL from response
            markdown_url = result_data.get("markdown_url")
            
            # Get markdown content
            markdown_response = requests.get(markdown_url)
            if markdown_response.status_code == 200:
                content = markdown_response.text
                st.session_state.extraction_metadata = {
                    "source_type": "pdf",
                    "markdown_url": markdown_url,
                    "parser": parsetype,
                    "chunking_strategy": chunking_strategy,
                    "vectordb": vectordb,
                    "timestamp": datetime.now().isoformat()
                }
                return content
            else:
                st.error("Failed to fetch markdown content")
                return None
        else:
            st.error(f"PDF Processing Error: {result_data.get('message', 'Unknown error')}")
            return None

    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return None

def scrape_website(api_en_url, api_op_url, url, scraping_type="enterprise"):
    """Scrape content from website"""
    try:
        if scraping_type == "enterprise":
            # Enterprise web scraping using API
            response = requests.post(
                f"{api_en_url}/web-scraping/enterprise",
                json={"url": url}
            )
            
            if response.status_code != 200:
                st.error(f"Web Scraping API Error: {response.json().get('detail', 'Unknown error')}")
                return None

            result = requests.post(
                f"{api_en_url}/web-process/",
                json={"md_path": response.json().get("saved_path")}
            )
            
            result_data = result.json()
            markdown_url = result_data.get("saved_path")
            
            if result_data["status"] == "success":
                markdown_response = requests.get(markdown_url)
                content = markdown_response.text
                st.session_state.extraction_metadata = {
                    "source_type": "web",
                    "source_url": url,
                    "markdown_file": markdown_url
                }
                return content
        else:
            # Open source web scraping using API
            response = requests.post(
                f"{api_op_url}/web-scraping/opensource",
                json={"url": url}
            )
            result = requests.post(
                f"{api_op_url}/web-process/opensource",
                json={"url": response.json().get("saved_path")}
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
                    "source_type": "web",
                    "source_url": url,
                    "markdown_file": markdown_url
                }
                return content

    except Exception as e:
        st.error(f"Error scraping website: {str(e)}")
        return None

def get_download_link(text, filename="extracted_content.md"):
    """Create download link for extracted content"""
    try:
        b64 = base64.b64encode(text.encode()).decode()
        return f'<a href="data:text/markdown;base64,{b64}" download="{filename}" class="download-button">Download Markdown File</a>'
    except Exception as e:
        st.error(f"Error creating download link: {str(e)}")
        return None

def store_document(doc_name, doc_type, processor=None):
    """Store document in session state for later use"""
    if 'parsed_documents' not in st.session_state:
        st.session_state.parsed_documents = {}
    
    st.session_state.parsed_documents[doc_name] = {
        "name": doc_name,
        "content": st.session_state.extracted_content,
        "metadata": st.session_state.extraction_metadata,
        "type": doc_type,
        "processor": processor,
        "timestamp": datetime.now().isoformat()
    }

def get_current_document():
    """Get the current document from session state"""
    if 'parsed_documents' in st.session_state and st.session_state.parsed_documents:
        # Get the last processed document
        doc_name = list(st.session_state.parsed_documents.keys())[-1]
        return st