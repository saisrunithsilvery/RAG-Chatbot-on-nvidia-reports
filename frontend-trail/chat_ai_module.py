import streamlit as st
import requests
import json
import os
from datetime import datetime
import random
import string

# Alternative function to generate a unique ID without using uuid
def generate_unique_id(length=12):
    """Generate a random ID string"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def estimate_cost(model, input_tokens, output_tokens):
    """Estimate cost based on token usage and model"""
    # Define pricing per 1K tokens
    model_pricing = {
        # OpenAI models
        "openai/gpt-4o": {"input": 0.01, "output": 0.03},
        "openai/gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "openai/gpt-4-mini": {"input": 0.002, "output": 0.006},  # Using mini instead of turbo
        
        # Anthropic models
        "anthropic/claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
        "anthropic/claude-3-sonnet-20240229": {"input": 0.008, "output": 0.024},
        
        # Perplexity model
        "perplexity/llama-3-sonar-small-32k": {"input": 0.0008, "output": 0.0016},  # Example pricing
        
        # DeepSeek model
        "deepseek/deepseek-coder": {"input": 0.0005, "output": 0.0015},  # Example pricing
        
        # Google Gemini models
        "google/gemini-pro": {"input": 0.0005, "output": 0.0015},
        "google/gemini-1.5-pro": {"input": 0.0005, "output": 0.0015},
        "google/gemini-ultra": {"input": 0.001, "output": 0.003}
    }
    
    # Get pricing for model or use default
    pricing = model_pricing.get(model, {"input": 0.01, "output": 0.03})
    
    # Calculate cost
    input_cost = (input_tokens / 1000) * pricing["input"]
    output_cost = (output_tokens / 1000) * pricing["output"]
    
    return input_cost + output_cost

def query_llm(prompt, model="gpt-4o", operation_type="chat"):
    """
    Send a query to the LLM API
    """
    API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8003')
    API_BACKEND_URL = os.getenv('API_BACKEND_URL', 'http://localhost:8003')
    PDF_API_URL = f"{API_BACKEND_URL}/pdf"
    
    try:
        # Check if active document exists
        if 'active_document' not in st.session_state or not st.session_state.active_document:
            st.error("No active document selected")
            return None
            
        # Prepare the payload based on operation type
        if operation_type == "chat" or operation_type == "ask_question":
            endpoint = f"{PDF_API_URL}/ask_question/"
            payload = {
                "folder_path": st.session_state.active_document.get("folder_path"),
                "content_id": st.session_state.active_document.get("content_id"),  # Always include content_id
                "question": prompt,
                "model": model,
                "max_tokens": 1000
            }
        
        elif operation_type == "summarize":
            # Get the content_id correctly
            content_id = st.session_state.active_document.get("content_id")
            
            endpoint = f"{PDF_API_URL}/summarize/"
            
            # Use a consistent approach to build the payload
            payload = {
                "folder_path": st.session_state.active_document.get("folder_path"),
                "content_id": content_id,  # Always include content_id
                "model": model,
                "max_length": 1000
            }

        elif operation_type == "extract_key_points":
            # Use the ask_question endpoint with a specific prompt
            endpoint = f"{PDF_API_URL}/ask_question/"
            payload = {
                "folder_path": st.session_state.active_document.get("folder_path"),
                "content_id": st.session_state.active_document.get("content_id"),  # Always include content_id
                "question": "Extract and list the key points from this document.",
                "model": model,
                "max_tokens": 1000
            }
        
        # Calculate start time for processing time tracking
        start_time = datetime.now()
        
        # Make the API request
        response = requests.post(endpoint, json=payload)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract token usage information - adapt to your API response structure
            if operation_type == "chat" or operation_type == "ask_question":
                text_field = "answer"
            else:
                text_field = "summary"
                
            input_tokens = result.get("usage", {}).get("prompt_tokens", 0)
            output_tokens = result.get("usage", {}).get("completion_tokens", 0)
            
            # Estimate cost based on model
            cost = estimate_cost(model, input_tokens, output_tokens)
            
            # Update total token usage for the session
            st.session_state.total_token_usage["input_tokens"] += input_tokens
            st.session_state.total_token_usage["output_tokens"] += output_tokens
            st.session_state.total_token_usage["estimated_cost"] += cost
            
            return {
                "text": result.get(text_field, ""),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "processing_time": processing_time,
                "model": model
            }
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error communicating with PDF API: {str(e)}")
        return None

def summarize_document(folder_path, model):
    """Generate a summary of the document"""
    with st.spinner("Generating document summary..."):
        API_BACKEND_URL = os.getenv('API_BACKEND_URL', 'http://localhost:8003')
        
        # Ensure we have the content_id
        if 'active_document' not in st.session_state or not st.session_state.active_document:
            st.error("No active document selected")
            return None
            
        # Get the content_id from active document
        content_id = st.session_state.active_document.get("content_id")
        
        # Prepare payload with explicit content_id
        payload = {
            "folder_path": folder_path,
            "content_id": content_id,  # Always include content_id
            "model": model,
            "max_length": 1000
        }
        
        # Calculate start time
        start_time = datetime.now()
        
        # Make API request
        response = requests.post(f"{API_BACKEND_URL}/pdf/summarize/", json=payload)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract token usage
            input_tokens = result.get("usage", {}).get("prompt_tokens", 0)
            output_tokens = result.get("usage", {}).get("completion_tokens", 0)
            cost = estimate_cost(model, input_tokens, output_tokens)
            
            # Update session token usage
            st.session_state.total_token_usage["input_tokens"] += input_tokens
            st.session_state.total_token_usage["output_tokens"] += output_tokens
            st.session_state.total_token_usage["estimated_cost"] += cost
            
            # Format result for chat history
            formatted_result = {
                "text": result["summary"],
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "processing_time": processing_time,
                "model": model
            }
            
            # Add to chat history
            st.session_state.chat_history.append({
                "role": "system",
                "content": "Document summary generated",
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": formatted_result["text"],
                "usage": {
                    "input_tokens": formatted_result["input_tokens"],
                    "output_tokens": formatted_result["output_tokens"],
                    "cost": formatted_result["cost"]
                },
                "model": model,
                "processing_time": formatted_result["processing_time"],
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            
            # Add to usage history
            if 'query_usage_history' not in st.session_state:
                st.session_state.query_usage_history = []
            
            st.session_state.query_usage_history.append({
                "query_type": "summarize",
                "query": "Document summary request",
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            return formatted_result
        else:
            st.error(f"Error generating summary: {response.text}")
            return None

def extract_key_points(folder_path, model):
    """Extract key points from the document"""
    with st.spinner("Extracting key points..."):
        API_BACKEND_URL = os.getenv('API_BACKEND_URL', 'http://localhost:8003')
        
        # Ensure we have the content_id
        if 'active_document' not in st.session_state or not st.session_state.active_document:
            st.error("No active document selected")
            return None
            
        # Get the content_id from active document
        content_id = st.session_state.active_document.get("content_id")
        
        # Use the ask_question endpoint with a specific question
        payload = {
            "folder_path": folder_path,
            "content_id": content_id,  # Always include content_id
            "question": "Extract and list the key points from this document.",
            "model": model,
            "max_tokens": 1000
        }
        
        # Calculate start time
        start_time = datetime.now()
        
        # Make API request
        response = requests.post(f"{API_BACKEND_URL}/pdf/ask_question/", json=payload)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract token usage
            input_tokens = result.get("usage", {}).get("prompt_tokens", 0)
            output_tokens = result.get("usage", {}).get("completion_tokens", 0)
            cost = estimate_cost(model, input_tokens, output_tokens)
            
            # Update session token usage
            st.session_state.total_token_usage["input_tokens"] += input_tokens
            st.session_state.total_token_usage["output_tokens"] += output_tokens
            st.session_state.total_token_usage["estimated_cost"] += cost
            
            # Format result for chat history
            formatted_result = {
                "text": result["answer"],
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "processing_time": processing_time,
                "model": model
            }
            
            # Add to chat history
            st.session_state.chat_history.append({
                "role": "system",
                "content": "Key points extracted",
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": formatted_result["text"],
                "usage": {
                    "input_tokens": formatted_result["input_tokens"],
                    "output_tokens": formatted_result["output_tokens"],
                    "cost": formatted_result["cost"]
                },
                "model": model,
                "processing_time": formatted_result["processing_time"],
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })
            
            # Add to usage history
            if 'query_usage_history' not in st.session_state:
                st.session_state.query_usage_history = []
            
            st.session_state.query_usage_history.append({
                "query_type": "keypoints",
                "query": "Key points extraction request",
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
            return formatted_result
        else:
            st.error(f"Error extracting key points: {response.text}")
            return None

def new_conversation():
    """Create a new conversation"""
    st.session_state.chat_history = []
    st.session_state.conversation_id = generate_unique_id()

def show_chat_ai():
    """Display the chat with AI page content"""
    
    # Apply chat AI specific styling
    st.markdown("""
        <style>
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

        /* Hide file uploader label and make the dropzone minimal */
        [data-testid="stFileUploader"] {
            width: auto !important;
        }

        /* Hide the unnecessary text */
        [data-testid="stFileUploader"] section > div {
            display: none;
        }

        /* Style just the icon/button area */
        [data-testid="stFileUploader"] section {
            padding: 0 !important;
            border: none !important;
            display: flex;
            justify-content: flex-end;
        }

        /* Style for the "Process" button to be compact */
        .process-btn {
            padding: 0 8px !important;
            height: 36px !important;
            margin-top: 2px !important;
        }

        /* Align text input and file uploader vertically */
        .input-row {
            display: flex;
            align-items: center;
        }

        /* Make sure the file uploader doesn't take too much space */
        .file-upload-col {
            width: auto !important;
            flex-shrink: 0 !important;
        }

        /* Style for the custom paperclip icon */
        .paperclip-icon {
            cursor: pointer;
            margin-top: 6px;
            margin-left: 5px;
            font-size: 24px;
            color: #666;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # API endpoints
    API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8003')
    API_BACKEND_URL = os.getenv('API_BACKEND_URL', 'http://localhost:8003')

    # Initialize session states
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
        
    if 'conversation_id' not in st.session_state:
        st.session_state.conversation_id = generate_unique_id()
        
    if 'parsed_documents' not in st.session_state:
        st.session_state.parsed_documents = {}
        
    if 'active_document' not in st.session_state:
        st.session_state.active_document = {}
    
    # Initialize available LLMs
    if 'available_llms' not in st.session_state:
        try:
            # Try to fetch from backend
            response = requests.get(f"{API_BACKEND_URL}/llm/models/")
            
            if response.status_code == 200:
                models = response.json()
                st.session_state.available_llms = []
                
                for model in models:
                    st.session_state.available_llms.append({
                        "id": model["id"],
                        "name": model["id"].split("/")[-1] if "/" in model["id"] else model["id"],
                        "provider": model["provider"].capitalize()
                    })
            else:
                # Fallback to default models
               st.session_state.available_llms = [
                {"id": "gpt-4o", "name": "GPT-4o", "provider": "OpenAI"},
                {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "provider": "OpenAI"},
                {"id": "gpt-4-mini", "name": "GPT-4 Mini", "provider": "OpenAI"},
                {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "provider": "Anthropic"},
                {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet", "provider": "Anthropic"},
                {"id": "gemini-pro", "name": "Gemini Pro", "provider": "Google"},
                {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "provider": "Google"},
                {"id": "llama-3-sonar-small-32k", "name": "Llama 3 Sonar Small", "provider": "Perplexity"},
                {"id": "deepseek-coder", "name": "DeepSeek Coder", "provider": "DeepSeek"}
            ]
        except Exception as e:
            # Fallback to default models if request fails
            st.session_state.available_llms = [
                {"id": "gpt-4o", "name": "GPT-4o", "provider": "OpenAI"},
                {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "provider": "OpenAI"},
                {"id": "gpt-4-mini", "name": "GPT-4 Mini", "provider": "OpenAI"},
                {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "provider": "Anthropic"},
                {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet", "provider": "Anthropic"},
                {"id": "gemini-pro", "name": "Gemini Pro", "provider": "Google"},
                {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "provider": "Google"},
                {"id": "llama-3-sonar-small-32k", "name": "Llama 3 Sonar Small", "provider": "Perplexity"},
                {"id": "deepseek-coder", "name": "DeepSeek Coder", "provider": "DeepSeek"}
            ]
    
    # Initialize token usage
    if 'total_token_usage' not in st.session_state:
        st.session_state.total_token_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "estimated_cost": 0.0
        }
    
    # Main layout
    st.title("🤖 Chat with AI")
    st.subheader("Ask questions about your documents")
    
    # Sidebar content specific to chat AI
    with st.sidebar:
        st.header("📊 Agent Settings")
        
        # LLM Model Selection
        llm_options = [(model["id"], f"{model['name']} ({model['provider']})") 
                        for model in st.session_state.available_llms]
        selected_model_option = st.selectbox(
            "Select LLM Model",
            options=[option[1] for option in llm_options],
            index=0
        )
        
        # Get the model ID from the selected option
        selected_model_index = [option[1] for option in llm_options].index(selected_model_option)
        llm_model_id = llm_options[selected_model_index][0]
        
        # Display token usage and pricing info
        st.info(f"Model usage is tracked and billed per token. Input tokens and output tokens have different pricing.")
        
        # Get model pricing from backend (in a real app)
        # For this example, we'll use hardcoded prices
        # model_prices = {
        #     "gpt-4o": {"input": "$0.01/1K tokens", "output": "$0.03/1K tokens"},
        #     "claude-3-sonnet-20240229": {"input": "$0.008/1K tokens", "output": "$0.024/1K tokens"},
        #     "gpt-3.5-turbo": {"input": "$0.0005/1K tokens", "output": "$0.0015/1K tokens"},
        #     "gemini-pro": {"input": "$0.0005/1K tokens", "output": "$0.0015/1K tokens"}
        # }
        model_pricing = {
        # OpenAI models
        "openai/gpt-4o": {"input": 0.01, "output": 0.03},
        "openai/gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "openai/gpt-4-mini": {"input": 0.002, "output": 0.006},  # Using mini instead of turbo
        
        # Anthropic models
        "anthropic/claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
        "anthropic/claude-3-sonnet-20240229": {"input": 0.008, "output": 0.024},
        
        # Perplexity model
        "perplexity/llama-3-sonar-small-32k": {"input": 0.0008, "output": 0.0016},  # Example pricing
        
        # DeepSeek model
        "deepseek/deepseek-coder": {"input": 0.0005, "output": 0.0015},  # Example pricing
        
        # Google Gemini models
        "google/gemini-pro": {"input": 0.0005, "output": 0.0015},
        "google/gemini-1.5-pro": {"input": 0.0005, "output": 0.0015},
        "google/gemini-ultra": {"input": 0.001, "output": 0.003}
    }
        
        # Show pricing for selected model
        if llm_model_id in model_pricing:
            price_info = model_pricing[llm_model_id]
            st.markdown(f"""
                **Pricing for selected model:**
                - Input: {price_info['input']}
                - Output: {price_info['output']}
            """)
            
        # Display current session usage
        st.markdown("**Current Session Usage:**")
        st.markdown(f"""
            - Input tokens: {st.session_state.total_token_usage['input_tokens']}
            - Output tokens: {st.session_state.total_token_usage['output_tokens']}
            - Est. cost: ${st.session_state.total_token_usage['estimated_cost']:.4f}
        """)
        
    
        st.markdown("---")
        
        st.header("📁 Document Manager")
        
        # Document Selection
        try:
            # Request document list from backend
            response = requests.get(f"{API_BACKEND_URL}/pdf/list_all_pdfs/")

            if response.status_code == 200:
                result = response.json()
                
                # Check if result is a dictionary with folder metadata
                if isinstance(result, dict) and len(result) > 0:
                    st.subheader(f"Available Documents ({len(result)})")
                    
                    # Create selection options
                    doc_options = {}
                    for content_id, doc_info in result.items():
                        folder_name = doc_info.get('folder_name', 'Unknown')
                        has_markdown = doc_info.get('has_markdown', False)
                        status = "✅" if has_markdown else "⏳"
                        
                        # Add status indicator to show if markdown is available
                        doc_options[f"{folder_name} {status}"] = {
                            "content_id": content_id,
                            "folder_path": doc_info.get('folder_path')
                        }
                    
                    selected_doc_name = st.selectbox("Select a document:", list(doc_options.keys()))
                    
                    if selected_doc_name and st.button("Set as Active Document", use_container_width=True):
                        selected_doc_info = doc_options[selected_doc_name]
                        selected_content_id = selected_doc_info["content_id"]
                        selected_folder_path = selected_doc_info["folder_path"]
                        
                        # Get document info
                        response = requests.post(
                            f"{API_BACKEND_URL}/pdf/select_pdfcontent/", 
                            json={
                                "content_id": selected_content_id,
                                "folder_path": selected_folder_path
                                }
                        )
                        
                        if response.status_code == 200:
                            doc_info = response.json()
                        
                            # Set as active document - ensure all required fields are present
                            st.session_state.active_document = {
                                "name": doc_info.get("folder_name", "Unknown Document"),
                                "id": selected_content_id,
                                "content_id": selected_content_id,  # Explicitly set content_id
                                "folder_path": selected_folder_path,
                                "type": "pdf",
                                "has_markdown": doc_info.get("has_markdown", False),
                                "markdown_content": doc_info.get("markdown_content", "")
                            }
                            
                            st.success(f"Document loaded: {doc_info.get('folder_name', 'Unknown Document')}")
                            st.rerun()
                else:
                    st.info("No documents available. Upload a PDF document to begin.")
            else:
                st.error(f"Error loading documents: {response.status_code}")
                
        except Exception as e:
            st.error(f"Error loading documents: {str(e)}")  # Display error message      
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
                <p>Document ID: {st.session_state.active_document["id"]}</p>
                <p>Content ID: {st.session_state.active_document["content_id"]}</p>
                <p>Folder Path: {st.session_state.active_document["folder_path"]}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Get Summary", type="primary", use_container_width=True):
                summarize_document(st.session_state.active_document["folder_path"], llm_model_id)
        
        with col2:
            if st.button("Extract Key Points", type="primary", use_container_width=True):
                extract_key_points(st.session_state.active_document["folder_path"], llm_model_id)
        
        with col3:
            if st.button("Generate Infographic", type="primary", use_container_width=True):
                st.info("Infographic generation will be implemented in a future update")
    else:
        st.warning("No document is currently active. Please select a document from the sidebar or upload a new document.")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Go to Data Parsing", type="primary", use_container_width=True):
                st.session_state.current_page = "data_parsing"
                st.rerun()
        
        with col2:
            if st.button("Get Summary", type="primary", use_container_width=True):
                st.info("Please select a document first to generate a summary.")
        
        with col3:
            if st.button("Extract Key Points", type="primary", use_container_width=True):
                st.info("Please select a document first to extract key points.")
    
    # Chat interface
    st.markdown("### Chat History")
    
    # Chat history with usage information
    chat_container = st.container()
    
    with chat_container:
        if st.session_state.chat_history:
            # Add a download button for the conversation history with usage data
            if st.button("📥 Download Conversation with Usage Data", key="download_history"):
                # Create a formatted version of the chat history with usage data
                import json
                import base64
                # from datetime import datetime
                
                # Format the chat history for download
                download_data = {
                    "conversation_id": st.session_state.conversation_id,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "active_document": st.session_state.active_document.get("name", "None"),
                    "messages": st.session_state.chat_history,
                    "token_usage": {
                        "total_input_tokens": st.session_state.total_token_usage["input_tokens"],
                        "total_output_tokens": st.session_state.total_token_usage["output_tokens"],
                        "total_cost": st.session_state.total_token_usage["estimated_cost"]
                    }
                }
                
                # Convert to JSON string
                json_str = json.dumps(download_data, indent=2)
                
                # Create download link
                b64 = base64.b64encode(json_str.encode()).decode()
                filename = f"conversation_{st.session_state.conversation_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                href = f'<a href="data:application/json;base64,{b64}" download="{filename}">Download JSON</a>'
                st.markdown(href, unsafe_allow_html=True)
        
        # Display usage summary if there are messages
        if 'query_usage_history' in st.session_state and st.session_state.query_usage_history:
            with st.expander("📊 View Query Usage History", expanded=False):
                st.markdown("### Query Usage History")
                
                # Create a markdown table header
                usage_table = """
                | Query Type | Query | Model | Input Tokens | Output Tokens | Cost | Timestamp |
                | ---------- | ----- | ----- | ------------ | ------------- | ---- | --------- |
                """
                
                # Add each query's usage data to the table
                for usage in st.session_state.query_usage_history:
                    usage_table += f"| {usage['query_type']} | {usage['query']} | {usage['model']} | {usage['input_tokens']:,} | {usage['output_tokens']:,} | ${usage['cost']:.4f} | {usage['timestamp']} |\n"
                
                st.markdown(usage_table)
                
                # Calculate and display totals
                total_input = sum(usage['input_tokens'] for usage in st.session_state.query_usage_history)
                total_output = sum(usage['output_tokens'] for usage in st.session_state.query_usage_history)
                total_cost = sum(usage['cost'] for usage in st.session_state.query_usage_history)
                
                st.markdown(f"""
                **Summary:**
                - Total Input Tokens: {total_input:,}
                - Total Output Tokens: {total_output:,}
                - Total Cost: ${total_cost:.4f}
                """)
        
        # Display the chat messages
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
                # Get model display name for the message
                model_id = message.get("model", "unknown")
                model_display_name = "Unknown Model"
                
                for model in st.session_state.available_llms:
                    if model["id"] == model_id:
                        model_display_name = f"{model['name']} ({model['provider']})"
                        break
                
                # Display the message with enhanced metadata
                st.markdown(
                    f"""
                    <div class="assistant-message">
                        <p>{message["content"]}</p>
                        <div class="message-metadata">
                            {message.get("timestamp", "")} • 
                            Model: {model_display_name} • 
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
    
    # User input and file upload section
    st.markdown("### Ask a Question or Upload a New Document")

    # Create a container for the input field and upload button
    input_container = st.container()

    with input_container:
        # Use custom HTML for the layout
        st.markdown("""
        <div class="input-row">
            <div style="flex-grow: 1; margin-right: 10px;">
                <!-- Leave space for Streamlit to inject the input box here -->
            </div>
            <div class="file-upload-col">
                <!-- Leave space for Streamlit to inject the file uploader here -->
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Create columns for the input field and submit button
        col1, col2 = st.columns([5, 1])
        
        with col1:
            user_input = st.text_input("", placeholder="Type your question here...", key="user_question")
            
        with col2:
            send_button = st.button("Send", key="send_question")
        
        # Handle question submission
        if send_button and user_input:
            # Check if document is selected
            if not st.session_state.active_document:
                st.warning("Please select a document first to ask questions about it.")
            else:
                # Add user message to chat history
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_input,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                })
                
                # Process the question
                with st.spinner("AI is thinking..."):
                    response = query_llm(user_input, model=llm_model_id, operation_type="ask_question")
                    
                    if response:
                        # Add assistant response to chat history
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": response["text"],
                            "usage": {
                                "input_tokens": response["input_tokens"],
                                "output_tokens": response["output_tokens"],
                                "cost": response["cost"]
                            },
                            "model": llm_model_id,
                            "processing_time": response["processing_time"],
                            "timestamp": datetime.now().strftime("%H:%M:%S")
                        })
                        
                        # Add to usage history
                        if 'query_usage_history' not in st.session_state:
                            st.session_state.query_usage_history = []
                        
                        st.session_state.query_usage_history.append({
                            "query_type": "question",
                            "query": user_input,
                            "model": llm_model_id,
                            "input_tokens": response["input_tokens"],
                            "output_tokens": response["output_tokens"],
                            "cost": response["cost"],
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                
                # Clear the input field
                if "user_question" in st.session_state:
                    del st.session_state.user_question
                st.rerun()
        
        # File upload section
        st.markdown("### Upload Document")
        uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"], key="pdf_uploader")
        
        if uploaded_file is not None:
            with st.spinner("Processing document..."):
                # Prepare the file for upload
                API_OP_URL = os.getenv('API_OP_URL', 'http://localhost:8001')
                
                try:
                    # Create a unique ID for this upload
                    upload_id = generate_unique_id()
                    
                    # Create form data for the file upload
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                    
                    # Make the API request to upload the file
                    response = requests.post(
                        f"{API_OP_URL}/pdf-process/opensource", 
                        files=files
                    )
                    if response.status_code != 200:
                        st.error(f"PDF Extraction API Error: {response.json().get('detail', 'Unknown error')}")
                        return None
                    
                    result_data = response.json()
                    
                    if result_data["status"] == "success":
                        result = response.json()
                        
                        st.success(f"Document uploaded successfully: {uploaded_file.name}")
                        
                        # # Add the document to the parsed documents list
                        # content_id = result.get("content_id")
                        # folder_path = result.get("folder_path")
                        
                        # # Set as active document - ensure content_id is explicitly set
                        # st.session_state.active_document = {
                        #     "name": uploaded_file.name,
                        #     "id": content_id,
                        #     "content_id": content_id,  # Explicitly set content_id
                        #     "folder_path": folder_path,
                        #     "type": "pdf",
                        #     "has_markdown": False  # Initially false until processing completes
                        # }
                        
                        # st.info("Document is being processed. It will be available for queries once processing completes.")
                       
                    else:
                        st.error(f"Error uploading document: {response.text}")
                except Exception as e:
                    st.error(f"Error during upload: {str(e)}")

# Entry point for the Streamlit application
def main():
    # Set page config
    st.set_page_config(
        page_title="Document AI Chat",
        page_icon="📄",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Check if current page is set
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "chat_ai"
    
    # Display the current page
    if st.session_state.current_page == "chat_ai":
        show_chat_ai()
    # Add other pages as needed
    
if __name__ == "__main__":
    main()