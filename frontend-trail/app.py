# app.py (Main Streamlit Application)
import streamlit as st
import requests
import pandas as pd
import json
import os
from datetime import datetime

# Configure page
st.set_page_config(
    page_title="NVIDIA Financial RAG System",
    page_icon="📈",
    layout="wide",
)

# API connection settings
API_URL = os.getenv("FASTAPI_URL", "http://fastapi:8000")

# Sidebar for navigation and configuration
st.sidebar.title("NVIDIA Financial RAG")
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/2/21/Nvidia_logo.svg/1280px-Nvidia_logo.svg.png", width=200)

# Main navigation
page = st.sidebar.radio(
    "Navigation",
    ["Home", "Data Management", "RAG Configuration", "Query System"]
)

# Reusable functions
def display_status(message, status_type="info"):
    """Display status messages with appropriate styling"""
    if status_type == "success":
        st.success(message)
    elif status_type == "error":
        st.error(message)
    elif status_type == "warning":
        st.warning(message)
    else:
        st.info(message)

def call_api(endpoint, method="GET", data=None, files=None):
    """Wrapper for API calls with error handling"""
    try:
        url = f"{API_URL}/{endpoint}"
        if method == "GET":
            response = requests.get(url, params=data)
        elif method == "POST":
            if files:
                response = requests.post(url, data=data, files=files)
            else:
                response = requests.post(url, json=data)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

# Home page
if page == "Home":
    st.title("NVIDIA Financial Reports RAG System")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ## Welcome to the NVIDIA Financial RAG System
        
        This application allows you to:
        - Upload NVIDIA quarterly reports
        - Configure different PDF parsing strategies
        - Use various RAG methods for information retrieval
        - Query specific financial information across quarters
        
        ### Getting Started
        1. Navigate to **Data Management** to upload or select reports
        2. Configure your RAG pipeline in **RAG Configuration**
        3. Ask questions about NVIDIA's financial data in **Query System**
        """)
    
    with col2:
        st.markdown("### System Status")
        # System status indicators
        system_status = call_api("status")
        if system_status:
            st.metric("Indexed Documents", system_status.get("indexed_documents", 0))
            st.metric("Available Quarters", system_status.get("available_quarters", 0))
            st.metric("Active Parser", system_status.get("active_parser", "None"))
            st.metric("Vector DB", system_status.get("vector_db", "Manual"))

# Data Management page
elif page == "Data Management":
    st.title("Data Management")
    
    tab1, tab2 = st.tabs(["Upload Reports", "Manage Existing Data"])
    
    with tab1:
        st.header("Upload NVIDIA Reports")
        
        # File uploader for PDF reports
        uploaded_files = st.file_uploader(
            "Upload NVIDIA quarterly reports (PDF format)", 
            type=["pdf"], 
            accept_multiple_files=True
        )
        
        if uploaded_files:
            # Form for upload configuration
            with st.form("upload_config"):
                # Quarters selection for uploaded files
                quarters = {}
                for i, file in enumerate(uploaded_files):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"File: {file.name}")
                    with col2:
                        year = st.selectbox(f"Year (File {i+1})", 
                                            range(datetime.now().year-10, datetime.now().year+1),
                                            index=5)
                        quarter = st.selectbox(f"Quarter (File {i+1})", ["Q1", "Q2", "Q3", "Q4"])
                        quarters[file.name] = f"{year}-{quarter}"
                
                # Parsing method selection
                parser = st.selectbox(
                    "PDF Parsing Method",
                    ["Assignment 1 Method", "Docling", "Mistral OCR"],
                    help="Select which technology to use for extracting text from PDFs"
                )
                
                submit = st.form_submit_button("Process Files")
                
                if submit and uploaded_files:
                    # Prepare files for API submission
                    files_data = []
                    for file in uploaded_files:
                        files_data.append(('files', (file.name, file.getvalue(), 'application/pdf')))
                    
                    # Send data to API
                    response = call_api(
                        endpoint="upload-documents",
                        method="POST",
                        data={"parser": parser, "quarters": json.dumps(quarters)},
                        files=files_data
                    )
                    
                    if response and response.get("status") == "success":
                        display_status(f"Successfully uploaded {len(uploaded_files)} files!", "success")
                        st.json(response.get("details", {}))
                    else:
                        display_status("Error uploading files. Please try again.", "error")
    
    with tab2:
        st.header("Manage Existing Data")
        
        # Get existing data information
        data_info = call_api("data-info")
        
        if data_info and data_info.get("documents"):
            # Display table of existing documents
            docs_df = pd.DataFrame(data_info["documents"])
            st.dataframe(docs_df)
            
            # Actions for existing documents
            with st.expander("Document Actions"):
                # Reprocess documents with different parser
                with st.form("reprocess_form"):
                    st.subheader("Reprocess Documents")
                    
                    doc_ids = st.multiselect(
                        "Select Documents to Reprocess",
                        options=docs_df["id"].tolist(),
                        format_func=lambda x: docs_df[docs_df["id"] == x]["filename"].iloc[0]
                    )
                    
                    new_parser = st.selectbox(
                        "New Parser Method",
                        ["Assignment 1 Method", "Docling", "Mistral OCR"]
                    )
                    
                    reprocess = st.form_submit_button("Reprocess Selected")
                    
                    if reprocess and doc_ids:
                        response = call_api(
                            "reprocess-documents",
                            method="POST",
                            data={"document_ids": doc_ids, "parser": new_parser}
                        )
                        
                        if response and response.get("status") == "success":
                            display_status("Documents queued for reprocessing", "success")
                        else:
                            display_status("Error reprocessing documents", "error")
                
                # Delete documents
                with st.form("delete_form"):
                    st.subheader("Delete Documents")
                    
                    delete_ids = st.multiselect(
                        "Select Documents to Delete",
                        options=docs_df["id"].tolist(),
                        format_func=lambda x: docs_df[docs_df["id"] == x]["filename"].iloc[0]
                    )
                    
                    st.warning("Warning: This will permanently delete the selected documents and their indexed data!")
                    
                    delete = st.form_submit_button("Delete Selected")
                    
                    if delete and delete_ids:
                        response = call_api(
                            "delete-documents",
                            method="POST",
                            data={"document_ids": delete_ids}
                        )
                        
                        if response and response.get("status") == "success":
                            display_status("Documents deleted successfully", "success")
                        else:
                            display_status("Error deleting documents", "error")
        else:
            st.info("No documents have been uploaded yet. Use the Upload Reports tab to add documents.")

# RAG Configuration page
elif page == "RAG Configuration":
    st.title("RAG Configuration")
    
    # Get current configuration
    config = call_api("get-configuration")
    
    with st.form("rag_config"):
        st.header("Configure RAG Pipeline")
        
        # Vector database selection
        vector_db = st.selectbox(
            "Vector Database",
            ["Manual (No Vector DB)", "Pinecone", "ChromaDB"],
            index=0 if not config else ["Manual (No Vector DB)", "Pinecone", "ChromaDB"].index(config.get("vector_db", "Manual (No Vector DB)"))
        )
        
        # Chunking strategy selection
        chunking_strategy = st.selectbox(
            "Chunking Strategy",
            ["Fixed Size Chunks", "Paragraph-based Chunks", "Semantic Chunks"],
            index=0 if not config else ["Fixed Size Chunks", "Paragraph-based Chunks", "Semantic Chunks"].index(config.get("chunking_strategy", "Fixed Size Chunks"))
        )
        
        # Additional configuration based on chunking strategy
        if chunking_strategy == "Fixed Size Chunks":
            chunk_size = st.slider("Chunk Size (characters)", 100, 2000, 500 if not config else config.get("chunk_size", 500))
            chunk_overlap = st.slider("Chunk Overlap (%)", 0, 50, 10 if not config else config.get("chunk_overlap", 10))
        
        # Embedding model selection
        embedding_model = st.selectbox(
            "Embedding Model",
            ["OpenAI Ada-002", "BERT", "Sentence Transformers"],
            index=0 if not config else ["OpenAI Ada-002", "BERT", "Sentence Transformers"].index(config.get("embedding_model", "OpenAI Ada-002"))
        )
        
        # LLM selection for response generation
        llm_model = st.selectbox(
            "LLM for Responses",
            ["OpenAI GPT-4", "Llama 2", "Mistral"],
            index=0 if not config else ["OpenAI GPT-4", "Llama 2", "Mistral"].index(config.get("llm_model", "OpenAI GPT-4"))
        )
        
        # Advanced options in expander
        with st.expander("Advanced Options"):
            top_k = st.slider("Number of chunks to retrieve (top-k)", 1, 20, 5 if not config else config.get("top_k", 5))
            similarity_threshold = st.slider("Similarity threshold", 0.0, 1.0, 0.7 if not config else config.get("similarity_threshold", 0.7))
            max_tokens = st.slider("Max tokens for response", 100, 2000, 500 if not config else config.get("max_tokens", 500))
        
        # Submit button
        submit_config = st.form_submit_button("Save Configuration")
        
        if submit_config:
            # Prepare configuration data
            config_data = {
                "vector_db": vector_db,
                "chunking_strategy": chunking_strategy,
                "embedding_model": embedding_model,
                "llm_model": llm_model,
                "top_k": top_k,
                "similarity_threshold": similarity_threshold,
                "max_tokens": max_tokens
            }
            
            # Add strategy-specific configuration
            if chunking_strategy == "Fixed Size Chunks":
                config_data["chunk_size"] = chunk_size
                config_data["chunk_overlap"] = chunk_overlap
            
            # Send configuration to API
            response = call_api(
                "update-configuration",
                method="POST",
                data=config_data
            )
            
            if response and response.get("status") == "success":
                display_status("Configuration saved successfully!", "success")
                
                # Trigger reindexing if needed
                if response.get("reindex_required", False):
                    st.warning("Configuration changes require reindexing. This may take some time.")
                    
                    if st.button("Reindex Now"):
                        reindex_response = call_api("reindex", method="POST")
                        if reindex_response and reindex_response.get("status") == "success":
                            display_status("Reindexing started. This may take several minutes.", "info")
                        else:
                            display_status("Error starting reindexing process", "error")
            else:
                display_status("Error saving configuration", "error")
    
    # Display current processing status
    with st.expander("Processing Status"):
        if st.button("Refresh Status"):
            process_status = call_api("process-status")
            if process_status:
                st.json(process_status)
            else:
                st.error("Could not retrieve process status")

# Query System page
elif page == "Query System":
    st.title("Query NVIDIA Financial Data")
    
    # Get available quarters for filtering
    quarters_data = call_api("available-quarters")
    available_quarters = quarters_data.get("quarters", []) if quarters_data else []
    
    # Query input section
    with st.form("query_form"):
        query = st.text_area(
            "Enter your question about NVIDIA's financial data",
            height=100,
            placeholder="Example: What was NVIDIA's revenue in Q2 2023?"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Quarter filtering
            selected_quarters = st.multiselect(
                "Filter by specific quarters (optional)",
                options=available_quarters,
                default=[]
            )
        
        with col2:
            # Response format options
            response_type = st.radio(
                "Response Format",
                ["Concise", "Detailed", "With References"]
            )
        
        # Submit button
        submit_query = st.form_submit_button("Ask Question")
        
        if submit_query and query:
            with st.spinner("Processing your question..."):
                # Prepare query data
                query_data = {
                    "query": query,
                    "quarters": selected_quarters if selected_quarters else [],
                    "response_type": response_type.lower()
                }
                
                # Send query to API
                response = call_api(
                    "query",
                    method="POST",
                    data=query_data
                )
                
                if response:
                    # Split the results tab for answer and sources
                    answer_tab, sources_tab = st.tabs(["Answer", "Source Documents"])
                    
                    with answer_tab:
                        st.markdown("### Answer")
                        st.markdown(response.get("answer", "No answer generated"))
                        
                        # Add metrics if available
                        if "metrics" in response:
                            st.markdown("---")
                            st.subheader("Key Metrics")
                            
                            metrics = response.get("metrics", {})
                            metric_cols = st.columns(len(metrics) if len(metrics) > 0 else 1)
                            
                            for i, (key, value) in enumerate(metrics.items()):
                                metric_cols[i % len(metric_cols)].metric(key, value)
                    
                    with sources_tab:
                        st.markdown("### Source Documents")
                        
                        sources = response.get("sources", [])
                        if sources:
                            for i, source in enumerate(sources):
                                with st.expander(f"Source {i+1}: {source.get('document', 'Unknown')} - {source.get('quarter', 'Unknown')}"):
                                    st.markdown(f"**Relevance Score:** {source.get('score', 0):.2f}")
                                    st.markdown(f"**Content:**")
                                    st.markdown(source.get("text", "No content available"))
                        else:
                            st.info("No source documents were used for this response.")
                else:
                    st.error("Error processing your query. Please try again.")
    
    # Query history
    with st.expander("Query History"):
        if st.button("Refresh History"):
            history = call_api("query-history")
            
            if history and history.get("queries"):
                history_df = pd.DataFrame(history["queries"])
                
                # Display history table
                st.dataframe(history_df[["timestamp", "query", "quarters"]])
                
                # Option to rerun previous queries
                selected_query = st.selectbox(
                    "Select a previous query to rerun",
                    options=range(len(history_df)),
                    format_func=lambda i: history_df.iloc[i]["query"]
                )
                
                if st.button("Rerun Selected Query"):
                    selected_query_data = history_df.iloc[selected_query].to_dict()
                    st.session_state.query = selected_query_data["query"]
                    st.experimental_rerun()
            else:
                st.info("No query history available yet.")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center;'>"
    "NVIDIA Financial RAG Pipeline | Built with Streamlit"
    "</div>", 
    unsafe_allow_html=True
)