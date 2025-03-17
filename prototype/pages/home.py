import streamlit as st
 
# Must be the first Streamlit command
st.set_page_config(
    page_title="DataNexus Pro | Home",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)
 
# Custom CSS for consistent styling
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
    
    /* Feature cards */
    .feature-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 20px;
        margin: 10px 0;
        border: 1px solid #eee;
    }
    
    .feature-card h3 {
        color: black !important;
        margin-bottom: 10px;
    }
    
    .feature-card p {
        color: #666 !important;
    }
    
    /* Navigation cards */
    .nav-card {
        background-color: #f8f9fa;
        border-radius: 12px;
        padding: 25px;
        margin: 15px 0;
        border: 1px solid #eee;
        text-align: center;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        cursor: pointer;
    }
    
    .nav-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
    }
    
    .nav-card h2 {
        color: black !important;
        margin-bottom: 15px;
    }
    
    .nav-card p {
        color: #666 !important;
    }
    
    .nav-card-icon {
        font-size: 3rem;
        margin-bottom: 15px;
        color: #4b8bf5;
    }
    
    /* Stats container */
    .stats-container {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 20px;
        margin: 20px 0;
        border: 1px solid #eee;
    }
    
    /* Metric styling */
    [data-testid="stMetricValue"] {
        color: black !important;
    }
    
    /* Button styling */
    .primary-button {
        background-color: #4b8bf5 !important;
        color: white !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 500 !important;
        text-align: center !important;
        transition: background-color 0.3s !important;
        width: 100% !important;
    }
    
    .primary-button:hover {
        background-color: #3a7ae0 !important;
    }
    
    .secondary-button {
        background-color: white !important;
        color: #4b8bf5 !important;
        border: 1px solid #4b8bf5 !important;
        border-radius: 4px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 500 !important;
        text-align: center !important;
        transition: background-color 0.3s !important;
        width: 100% !important;
    }
    
    .secondary-button:hover {
        background-color: rgba(75, 139, 245, 0.1) !important;
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
    
    /* Sidebar navigation styling */
    [data-testid="stSidebar"] {
        background-color: white;
    }
    
    /* Navigation items in sidebar */
    .css-17lntkn {
        color: #A9A9A9 !important;
        font-weight: normal;
    }
    
    /* Fix for the uploaded file name color in the file uploader */
    [data-testid="stFileUploader"] div {
        color: black !important; /* Ensure the file name is visible */
        font-weight: 500;        /* Adjust font weight as needed */
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
        background-color: #f8f9fa;  /* Light background for better visibility */
        border: 1px solid #ddd;      /* Light border */
        border-radius: 4px;
    }
    </style>
""", unsafe_allow_html=True)
 
# Initialize session state if needed
if 'welcome_shown' not in st.session_state:
    st.session_state.welcome_shown = False
 
# Main content
st.markdown("""
    <div style='padding: 1rem 0;'>
        <h1 style='color: black; font-size: 2.5rem; font-weight: 800;'>📊 DataNexus Pro</h1>
        <p style='color: #666; font-size: 1.2rem;'>Unified Data Extraction Platform</p>
    </div>
""", unsafe_allow_html=True)

# Navigation options
st.markdown("### Choose an Option")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
        <div class='nav-card' id='data-parsing-card'>
            <div class='nav-card-icon'>📄</div>
            <h2>Data Parsing</h2>
            <p>Extract and process data from PDFs and websites</p>
            <ul style='text-align: left; color: #666;'>
                <li>PDF text extraction</li>
                <li>Table recognition</li>
                <li>Web scraping</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Go to Data Parsing", key="data_parsing_btn", help="Extract data from PDFs and websites", use_container_width=True, type="primary"):
        st.switch_page("pages/data_parsing.py")

with col2:
    st.markdown("""
        <div class='nav-card' id='chat-ai-card'>
            <div class='nav-card-icon'>🤖</div>
            <h2>Chat with AI</h2>
            <p>Interact with AI to analyze your documents</p>
            <ul style='text-align: left; color: #666;'>
                <li>Document summaries</li>
                <li>Ask questions about content</li>
                <li>Generate insights</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("Go to AI Chat", key="chat_ai_btn", help="Chat with AI about your documents", use_container_width=True, type="primary"):
        st.switch_page("pages/chat_ai.py")

# Platform overview section
st.markdown("### Transform Your Data Processing")
st.markdown("""
    DataNexus Pro simplifies the extraction and analysis of data from various sources.
    Our platform provides advanced tools for both PDF extraction and web scraping,
    making data processing more efficient than ever.
""")
 
# Feature highlights
col1, col2, col3 = st.columns(3)
 
with col1:
    st.markdown("""
        <div class='feature-card'>
            <h3>📄 PDF Processing</h3>
            <p>Extract text, tables, and images from PDF documents with high accuracy</p>
            <ul style='color: #666;'>
                <li>Table extraction</li>
                <li>Image extraction</li>
                <li>Text analysis</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)
 
with col2:
    st.markdown("""
        <div class='feature-card'>
            <h3>🌐 Web Scraping</h3>
            <p>Collect data from websites efficiently and reliably</p>
            <ul style='color: #666;'>
                <li>Structured data extraction</li>
                <li>Dynamic content handling</li>
                <li>Custom scraping rules</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)
 
with col3:
    st.markdown("""
        <div class='feature-card'>
            <h3>🤖 AI Assistant</h3>
            <p>Leverage AI to understand and analyze your documents</p>
            <ul style='color: #666;'>
                <li>Document summarization</li>
                <li>Question answering</li>
                <li>Key point extraction</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)
 
# Platform statistics
st.markdown("### Platform Statistics")
st.markdown("""
    <div class='stats-container'>
        <div style='display: flex; justify-content: space-between;'>
""", unsafe_allow_html=True)
 
col1, col2, col3, col4 = st.columns(4)
 
with col1:
    st.metric("Documents Processed", "10K+")
with col2:
    st.metric("Active Users", "500+")
with col3:
    st.metric("Time Saved", "1000+ hrs")
with col4:
    st.metric("Accuracy Rate", "99.9%")
 
# Sidebar
with st.sidebar:
    st.markdown("### 🏠 Home")
    
    st.markdown("### Quick Navigation")
    
    if st.button("📄 Data Parsing", key="sidebar_data", use_container_width=True):
        st.switch_page("pages/data_parsing.py")
        
    if st.button("🤖 Chat with AI", key="sidebar_chat", use_container_width=True):
        st.switch_page("pages/chat_ai.py")