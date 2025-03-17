import streamlit as st
import home_module
import data_parsing_module
import chat_ai_module
import os
import sys
import json
import requests

# Must be the first Streamlit command
st.set_page_config(
    page_title="DataNexus Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply global styling
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
    
    /* Navigation items in sidebar */
    .css-17lntkn {
        color: #A9A9A9 !important;
        font-weight: normal;
    }
    
    /* Selected navigation item */
    .css-17lntkn.selected {
        background-color: rgba(240, 242, 246, 0.5) !important;
        border-radius: 4px;
    }
    
    /* Main content text */
    h1, h2, h3, p {
        color: black !important;
    }
    
    /* Make header white */
    header[data-testid="stHeader"] {
        background-color: white;
    }
    
    /* Remove any dark backgrounds */
    .stApp header {
        background-color: white !important;
    }
    
    /* Style header elements */
    .stApp header button {
        color: black !important;
    }
    
    /* Fix for the uploaded file name color in the file uploader */
    [data-testid="stFileUploader"] div {
        color: black !important;
        font-weight: 500;
    }
     
    /* Adjust the input and dropdown text color */
    .stTextInput, .stSelectbox {
        color: black !important;
        background-color: white !important;
    }
     
    /* Ensure that all text within the sidebar is visible */
    [data-testid="stSidebar"] * {
        color: black !important;
    }
     
    /* General fix for button and interactive element text */
    .stRadio > div, .stSelectbox > div {
        color: black !important;
        background-color: white !important;
    }
     
    /* Specific styling for the file uploader */
    .stFileUploader {
        background-color: #f8f9fa;
        border: 1px solid #ddd;
        border-radius: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state for navigation and app state
if 'current_page' not in st.session_state:
    st.session_state.current_page = "home"

# Initialize other session states
if 'extracted_content' not in st.session_state:
    st.session_state.extracted_content = ""
if 'extraction_metadata' not in st.session_state:
    st.session_state.extraction_metadata = {}
if 'parsed_documents' not in st.session_state:
    st.session_state.parsed_documents = {}
if 'active_document' not in st.session_state:
    st.session_state.active_document = {}
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'available_llms' not in st.session_state:
    # This would ideally come from an API call to the backend
    st.session_state.available_llms = [
        {"id": "gpt-4o", "name": "GPT-4o", "provider": "OpenAI"},
        {"id": "claude-3-5-sonnet", "name": "Claude 3.5 Sonnet", "provider": "Anthropic"},
        {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "provider": "OpenAI"},
        {"id": "llama-3-70b", "name": "Llama 3 70B", "provider": "Meta"}
    ]

# Environment variables - FastAPI backend endpoints
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
API_BACKEND_URL = os.getenv('API_BACKEND_URL', 'http://localhost:8000')
LLM_API_URL = f"{API_BACKEND_URL}/llm"
PDF_API_URL = f"{API_BACKEND_URL}/pdf"
DOCUMENT_API_URL = f"{API_BACKEND_URL}/document"

# Model pricing information (per 1K tokens)
MODEL_PRICING = {
    "gpt-4o": {"input": 0.01, "output": 0.03},
    "claude-3-5-sonnet": {"input": 0.008, "output": 0.024},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "llama-3-70b": {"input": 0.0007, "output": 0.0009}
}

# Initialize token usage tracking
if 'total_token_usage' not in st.session_state:
    st.session_state.total_token_usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "estimated_cost": 0.0
    }

# Initialize query usage history
if 'query_usage_history' not in st.session_state:
    st.session_state.query_usage_history = []

# Cache available LLMs from the backend
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_available_llms():
    try:
        response = requests.get(f"{LLM_API_URL}/models")
        if response.status_code == 200:
            return response.json()
        return st.session_state.available_llms  # Fallback to predefined models
    except Exception as e:
        print(f"Error fetching LLM models: {e}")
        return st.session_state.available_llms

# Try to fetch available LLMs
try:
    st.session_state.available_llms = fetch_available_llms()
except:
    # Keep the default models if fetch fails
    pass

# Sidebar navigation
with st.sidebar:
    st.markdown("### Navigation")
    
    if st.button("🏠 Home", key="nav_home", use_container_width=True):
        st.session_state.current_page = "home"
        st.rerun()
        
    if st.button("📄 Data Parsing", key="nav_data", use_container_width=True):
        st.session_state.current_page = "data_parsing"
        st.rerun()
        
    if st.button("🤖 Chat with AI", key="nav_chat", use_container_width=True):
        st.session_state.current_page = "chat_ai"
        st.rerun()
    
    
# Update the last part of your main.py file:

# Render the current page
if st.session_state.current_page == "home":
    home_module.show_home()
elif st.session_state.current_page == "data_parsing":
    data_parsing_module.show_data_parsing()
elif st.session_state.current_page == "chat_ai":
    # Make sure we're calling the function correctly without any parameters
    chat_ai_module.show_chat_ai()