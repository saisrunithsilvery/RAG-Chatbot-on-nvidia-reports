import streamlit as st
import requests
import json
import os
import datetime
import uuid

# Set page config first
st.set_page_config(
    page_title="DataNexus Pro | Chat with AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API endpoints
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
LLM_API_URL = f"{API_BASE_URL}/llm"

# Initialize session states
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
    
if 'conversation_id' not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
    
if 'parsed_documents' not in st.session_state:
    st.session_state.parsed_documents = {}
    
if 'active_document' not in st.session_state:
    st.session_state.active_document = {}

# Function to call LLM API
def query_llm(prompt, model="gpt-4o", document_content=None, operation_type="chat"):
    """
    Send a query to the LLM API
    Parameters:
    - prompt: The user's question or instruction
    - model: LLM model to use
    - document_content: Document content for context
    - operation_type: Type of operation (chat, summarize, extract_key_points)
    """
    try:
        payload = {
            "prompt": prompt,
            "model": model,
            "operation_type": operation_type,
            "conversation_id": st.session_state.conversation_id
        }
        
        # Include document content if available
        if document_content:
            payload["document_content"] = document_content
            
        response = requests.post(
            f"{LLM_API_URL}/generate",
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            return {
                "text": result.get("response", ""),
                "input_tokens": result.get("usage", {}).get("input_tokens", 0),
                "output_tokens": result.get("usage", {}).get("output_tokens", 0),
                "cost": result.get("usage", {}).get("cost", 0),
                "processing_time": result.get("processing_time", 0)
            }
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error communicating with LLM API: {str(e)}")
        return None

# Function to create a new conversation
def new_conversation():
    st.session_state.chat_history = []
    st.session_state.conversation_id = str(uuid.uuid4())

# Function to summarize document
def summarize_document(document_content, model):
    with st.spinner("Generating document summary..."):
        result = query_llm(
            prompt="Provide a comprehensive summary of this document.",
            model=model,
            document_content=document_content,
            operation_type="summarize"
        )
        
        if result:
            # Add to chat history
            st.session_state.chat_history.append({
                "role": "system",
                "content": "Document summary generated",
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            })
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": result["text"],
                "usage": {
                    "input_tokens": result["input_tokens"],
                    "output_tokens": result["output_tokens"],
                    "cost": result["cost"]
                },
                "processing_time": result["processing_time"],
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            })
            return result
        return None

# Function to extract key points
def extract_key_points(document_content, model):
    with st.spinner("Extracting key points..."):
        result = query_llm(
            prompt="Extract the key points from this document.",
            model=model,
            document_content=document_content,
            operation_type="extract_key_points"
        )
        
        if result:
            # Add to chat history
            st.session_state.chat_history.append({
                "role": "system",
                "content": "Key points extracted",
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            })
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": result["text"],
                "usage": {
                    "input_tokens": result["input_tokens"],
                    "output_tokens": result["output_tokens"],
                    "cost": result["cost"]
                },
                "processing_time": result["processing_time"],
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
            })
            return result
        return None

# Apply styling
st.markdown("""
    <style>
    /* Global styles */
    .stApp {
        background-color: white;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: white;
    }
    
    /* Main content text */
    h1, h2, h3, p {
        color: black !important;
    }
    
    /* Chat styling */
    .chat-container {
        margin-bottom: 20px;
        max-height: 600px;
        overflow-y: auto;
    }
    
    .user-message {
        background-color: #f0f2f6;
        border-radius: 18px;
        padding: 10px 15px;
        margin: 5px 0;
        margin-left: 40px;
        margin-right: 20px;
        text-align: right;
    }
    
    .assistant-message {
        background-color: #f8fbff;
        border: 1px solid #e6e9f0;
        border-radius: 8px;
        padding: 10px 15px;
        margin: 5px 0;
        margin-right: 40px;
    }
    
    .system-message {
        background-color: #f5f7fa;
        border-radius: 4px;
        padding: 5px 10px;
        margin: 5px 0;
        text-align: center;
        color: #666;
        font-size: 12px;
    }
    
    .message-metadata {
        font-size: 12px;
        color: #666;
        margin-top: 5px;
    }
    
    /* Usage metrics panel */
    .metrics-panel {
        background-color: #f8f9fa;
        border-radius: 4px;
        padding: 10px;
        margin: 10px 0;
        display: flex;
        justify-content: space-between;
    }
    
    .metric-item {
        text-align: center;
    }
    
    /* Document selection */
    .document-selector {
        background-color: #f5f7fa;
        border-radius: 4px;
        padding: 15px;
        margin-bottom: 15px;
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
    
    /* Button styling */
    .primary-button {
        background-color: #4b8bf5 !important;
        color: white !important;
    }
    
    .primary-button:hover {
        background-color: #3a7ae0 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Main layout
st.title("🤖 Chat with AI")
st.subheader("Ask questions about your documents")

# Sidebar
with st.sidebar:
    st.markdown("### Navigation")
    
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("home.py")
    
    if st.button("📄 Data Parsing", use_container_width=True):
        st.switch_page("pages/data_parsing.py")
    
    st.markdown("""<div class="nav-highlight">🤖 Chat with AI</div>""", unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.header("📊 Agent Settings")
    
    # LLM Model Selection
    llm_model = st.selectbox(
        "Select LLM Model",
        ["GPT-4o", "Claude 3.5 Sonnet", "GPT-3.5 Turbo", "Llama 3 70B"]
    )
    
    # Agent Type Selection
    agent_type = st.selectbox(
        "Select Agent Type",
        ["multi-modal-rag", "simple-chat", "advanced-research"]
    )
    
    st.markdown("---")
    
    st.header("📁 Document Manager")
    
    # Document Selection
    if st.session_state.parsed_documents:
        st.subheader("Select and Download PDFs")
        
        doc_names = list(st.session_state.parsed_documents.keys())
        selected_doc = st.selectbox("Select a PDF document:", doc_names)
        
        if selected_doc:
            doc_info = st.session_state.parsed_documents[selected_doc]
            st.text(f"Size: {len(doc_info['content']) // 1000} KB")
            
            if st.button("Set as Active Document", use_container_width=True):
                st.session_state.active_document = {
                    "name": selected_doc,
                    "content": doc_info["content"],
                    "type": doc_info["type"]
                }
                st.rerun()
    else:
        st.info("No documents parsed yet. Go to Data Parsing to extract content first.")
    
    # Conversation Controls
    st.markdown("---")
    st.header("💬 Conversation")
    
    if st.button("New Chat", use_container_width=True):
        new_conversation()
        st.rerun()

# Main content area
# Document Information
if st.session_state.active_document:
    st.markdown(
        f"""
        <div class="document-selector">
            <p><strong>Current Document:</strong> {st.session_state.active_document["name"]} 
            ({st.session_state.active_document["type"].upper()})</p>
            <p>Content Length: {len(st.session_state.active_document["content"]) // 1000} KB</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Get Summary", type="primary", use_container_width=True):
            summarize_document(st.session_state.active_document["content"], llm_model.lower().replace(" ", "-"))
    
    with col2:
        if st.button("Extract Key Points", type="primary", use_container_width=True):
            extract_key_points(st.session_state.active_document["content"], llm_model.lower().replace(" ", "-"))
    
    with col3:
        if st.button("Generate Infographic", type="primary", use_container_width=True):
            st.info("Infographic generation will be implemented in a future update")
else:
    st.warning("No document is currently active. Please select a document from the sidebar or parse a new document.")
    if st.button("Go to Data Parsing", type="primary"):
        st.switch_page("pages/data_parsing.py")

# Chat interface
st.markdown("### Chat History")

# Display chat history
chat_container = st.container()

with chat_container:
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            st.markdown(
                f"""
                <div class="user-message">
                    <p>{message["content"]}</p>
                    <div class="message-metadata">{message["timestamp"]}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        elif message["role"] == "assistant":
            st.markdown(
                f"""
                <div class="assistant-message">
                    <p>{message["content"]}</p>
                    <div class="message-metadata">
                        {message.get("timestamp", "")} • 
                        Model: {llm_model} • 
                        Tokens: {message.get("usage", {}).get("input_tokens", 0)} in / 
                        {message.get("usage", {}).get("output_tokens", 0)} out • 
                        Cost: ${message.get("usage", {}).get("cost", 0):.4f} • 
                        Time: {message.get("processing_time", 0):.1f}s
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        elif message["role"] == "system":
            st.markdown(
                f"""
                <div class="system-message">
                    {message["content"]} • {message["timestamp"]}
                </div>
                """,
                unsafe_allow_html=True
            )

# User input
st.markdown("### Ask a Question")
user_question = st.text_input(
    "Type your question about the document",
    placeholder="What is the main topic of this document?",
    key="user_question_input"
)

if st.button("Ask", type="primary") and user_question:
    if not st.session_state.active_document:
        st.error("Please select a document first.")
    else:
        # Add user message to chat history
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_question,
            "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
        })
        
        # Call LLM API
        with st.spinner("Thinking..."):
            result = query_llm(
                prompt=user_question,
                model=llm_model.lower().replace(" ", "-"),
                document_content=st.session_state.active_document["content"],
                operation_type="chat"
            )
            
            if result:
                # Add assistant response to chat history
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": result["text"],
                    "usage": {
                        "input_tokens": result["input_tokens"],
                        "output_tokens": result["output_tokens"],
                        "cost": result["cost"]
                    },
                    "processing_time": result["processing_time"],
                    "timestamp": datetime.datetime.now().strftime("%H:%M:%S")
                })
                
                # Clear the input field
                st.session_state.user_question_input = ""
                
                # Rerun to update the chat display
                st.rerun()