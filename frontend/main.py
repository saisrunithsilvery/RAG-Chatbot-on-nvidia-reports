import streamlit as st
import home_module
import data_parsing_module
import chat_ai_module
import redis_helper
import os
import sys
import json
import requests
import importlib

# Ensure redis_helper is properly initialized
if "redis_helper" in sys.modules:
    importlib.reload(redis_helper)

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

# Environment variables - FastAPI backend endpoints
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
API_BACKEND_URL = os.getenv('API_BACKEND_URL', 'http://localhost:8000')
LLM_API_URL = f"{API_BACKEND_URL}/llm"
PDF_API_URL = f"{API_BACKEND_URL}/pdf"
DOCUMENT_API_URL = f"{API_BACKEND_URL}/document"

# Define hardcoded models instead of fetching from API
def fetch_available_llms():
    """Return the predefined list of available models without making API calls"""
    return [
        {"id": "openai/gpt-4o", "name": "GPT-4o", "provider": "OpenAI"},
        {"id": "openai/gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "provider": "OpenAI"},
        {"id": "openai/gpt-4-mini", "name": "GPT-4 Mini", "provider": "OpenAI"},
        {"id": "anthropic/claude-3-opus-20240229", "name": "Claude 3 Opus", "provider": "Anthropic"},
        {"id": "anthropic/claude-3-sonnet-20240229", "name": "Claude 3 Sonnet", "provider": "Anthropic"},
        {"id": "perplexity/llama-3-sonar-small-32k", "name": "Llama 3 Sonar Small 32k", "provider": "Perplexity"},
        {"id": "deepseek/deepseek-coder", "name": "DeepSeek Coder", "provider": "DeepSeek"},
        {"id": "google/gemini-pro", "name": "Gemini Pro", "provider": "Google"},
        {"id": "google/gemini-1.5-pro", "name": "Gemini 1.5 Pro", "provider": "Google"},
        {"id": "google/gemini-ultra", "name": "Gemini Ultra", "provider": "Google"}
    ]

# Initialize available LLMs
if 'available_llms' not in st.session_state:
    st.session_state.available_llms = fetch_available_llms()

# Model pricing information (per 1K tokens)
MODEL_PRICING = {
    "openai/gpt-4o": {"input": 0.01, "output": 0.03},
    "openai/gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "openai/gpt-4-mini": {"input": 0.002, "output": 0.006},
    "anthropic/claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
    "anthropic/claude-3-sonnet-20240229": {"input": 0.008, "output": 0.024},
    "perplexity/llama-3-sonar-small-32k": {"input": 0.0008, "output": 0.0016},
    "deepseek/deepseek-coder": {"input": 0.0005, "output": 0.0015},
    "google/gemini-pro": {"input": 0.0005, "output": 0.0015},
    "google/gemini-1.5-pro": {"input": 0.0005, "output": 0.0015},
    "google/gemini-ultra": {"input": 0.001, "output": 0.003}
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

# Set available LLMs (directly using the function instead of API call)
st.session_state.available_llms = fetch_available_llms()

# Redis repair widget function
def add_redis_repair_widget():
    """Add a widget to manually repair Redis database info"""
    with st.sidebar.expander("🛠️ Redis Repair Tools", expanded=False):
        st.write("Fix database and collection information in Redis")
        
        # Show current status
        status = redis_helper.debug_redis_status()
        
        # Format the status data
        redis_db = "NULL"
        redis_collection = "NULL"
        session_db = st.session_state.get("selected_db", "NULL")
        session_collection = st.session_state.get("collection_name", "NULL")
        
        # Try to get values from Redis
        if status.get("parsed_value"):
            redis_db = status.get("parsed_value").get("db", "NULL")
            redis_collection = status.get("parsed_value").get("collection_name", "NULL")
        
        st.write("Current status:")
        st.json({
            "Redis DB": redis_db,
            "Redis Collection": redis_collection,
            "Session DB": session_db,
            "Session Collection": session_collection
        })
        
        # Option 1: Repair from session state
        if st.button("Repair from Session State"):
            if 'selected_db' in st.session_state and st.session_state.selected_db:
                result = redis_helper.set_db_info(
                    st.session_state.selected_db,
                    st.session_state.collection_name
                )
                if result:
                    st.success("✅ Redis repaired from session state")
                    st.rerun()
                else:
                    st.error("❌ Failed to repair Redis")
            else:
                st.warning("⚠️ No database in session state")
        
        # Option 2: Manual values
        st.write("Or set values manually:")
        manual_db = st.text_input("Database name:", 
                                  value=st.session_state.get("selected_db", ""))
        manual_collection = st.text_input("Collection name:", 
                                         value=st.session_state.get("collection_name", ""))
        
        if st.button("Update Redis with Manual Values"):
            if manual_db:
                result = redis_helper.set_db_info(manual_db, manual_collection)
                if result:
                    # Also update session state
                    st.session_state.selected_db = manual_db
                    st.session_state.collection_name = manual_collection
                    st.success(f"✅ Redis updated with DB={manual_db}")
                    st.rerun()
                else:
                    st.error("❌ Failed to update Redis")
            else:
                st.error("❌ Database name cannot be empty")
                
        # Option 3: Clear Redis
        if st.button("Clear Redis Data", type="secondary"):
            try:
                session_id = redis_helper.get_session_id()
                key = f"session:{session_id}:db_info"
                if redis_helper.REDIS_AVAILABLE and redis_helper.redis_client:
                    redis_helper.redis_client.delete(key)
                    st.success("✅ Redis data cleared")
                    st.rerun()
                else:
                    st.error("Redis not available")
            except Exception as e:
                st.error(f"❌ Failed to clear Redis: {str(e)}")

# Display Redis status information in a collapsed expander
with st.sidebar.expander("Redis Status", expanded=False):
    # Display Redis connection status
    if redis_helper.REDIS_AVAILABLE:
        st.success("✅ Redis Connected")
        
        # Show Redis connection details
        st.info(f"Session ID: {redis_helper.get_session_id()}")
        
        # Check if DB info exists
        redis_debug = redis_helper.debug_redis_status()
        if redis_debug.get("parsed_value"):
            db_info = redis_debug.get("parsed_value")
            st.write("Redis Data:")
            st.json(db_info)
            
            # Check for missing DB value but valid collection
            if not db_info.get("db") and db_info.get("collection_name"):
                st.warning("⚠️ DB value is missing in Redis")
                if st.button("Auto-repair"):
                    if redis_helper.repair_db_info():
                        st.success("Redis data repaired!")
                        st.rerun()
        else:
            st.warning("No data in Redis")
    else:
        st.error("❌ Redis Not Connected")

# Add Redis repair widget
add_redis_repair_widget()

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

# Render the current page
if st.session_state.current_page == "home":
    home_module.show_home()
elif st.session_state.current_page == "data_parsing":
    data_parsing_module.show_data_parsing()
elif st.session_state.current_page == "chat_ai":
    # Make sure we're calling the function correctly without any parameters
    chat_ai_module.show_chat_ai()