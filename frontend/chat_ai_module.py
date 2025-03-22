import streamlit as st
import requests
import os
import sys
import importlib
from datetime import datetime
import random
import string
import redis_helper
import traceback

# Ensure redis_helper is properly initialized but don't expose to UI
if "redis_helper" in sys.modules:
    importlib.reload(redis_helper)

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
        "gpt-4o": {"input": 0.01, "output": 0.03},
        "openai/gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "openai/gpt-4-mini": {"input": 0.002, "output": 0.006},
        "gpt-4-mini": {"input": 0.002, "output": 0.006},
        
        # Anthropic models
        "anthropic/claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
        "claude-3-opus-20240229": {"input": 0.015, "output": 0.075},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "anthropic/claude-3-sonnet-20240229": {"input": 0.008, "output": 0.024},
        "claude-3-sonnet-20240229": {"input": 0.008, "output": 0.024},
        "claude-3-sonnet": {"input": 0.008, "output": 0.024},
        
        # Perplexity model
        "perplexity/llama-3-sonar-small-32k": {"input": 0.0008, "output": 0.0016},
        "llama-3-sonar-small-32k": {"input": 0.0008, "output": 0.0016},
        
        # DeepSeek model
        "deepseek/deepseek-coder": {"input": 0.0005, "output": 0.0015},
        "deepseek-coder": {"input": 0.0005, "output": 0.0015},
        
        # Google Gemini models
        "google/gemini-pro": {"input": 0.0005, "output": 0.0015},
        "gemini-pro": {"input": 0.0005, "output": 0.0015},
        "google/gemini-1.5-pro": {"input": 0.0005, "output": 0.0015},
        "gemini-1.5-pro": {"input": 0.0005, "output": 0.0015},
        "google/gemini-ultra": {"input": 0.001, "output": 0.003},
        "gemini-ultra": {"input": 0.001, "output": 0.003}
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
    # Get API URL from environment or use default
    QUERY_API_URL = os.getenv('QUERY_SERVICE_URL', 'http://localhost:8005/query')
    
    # Debug output - print environment variables
    st.write(f"Using API URL: {QUERY_API_URL}")
    
    try:
        # First check if we can reach the API
        base_url = QUERY_API_URL.split('/query')[0] if '/query' in QUERY_API_URL else QUERY_API_URL
        health_url = f"{base_url}/health"
        
        try:
            health_response = requests.get(health_url, timeout=5)
            # st.write(f"API Health Check: {health_response.status_code}")
        except Exception as health_error:
            # st.error(f"API Health Check Failed: {str(health_error)}")
            # Continue anyway since health endpoint might not exist
            st.write("Querying API...")
        
        # Check Redis for latest database info
        db_info = None
        try:
            # Only try Redis if it's available
            if hasattr(redis_helper, 'REDIS_AVAILABLE') and redis_helper.REDIS_AVAILABLE:
                redis_helper.force_sync_session_with_redis()
                db_info = redis_helper.get_db_info()
                st.write(f"Redis DB Info: {db_info}")
            else:
                st.write("Redis is not available")
        except Exception as redis_error:
            st.error(f"Redis Error: {str(redis_error)}")
            # Continue without Redis
        
        # Get database info from session state as fallback
        if not db_info and 'selected_db' in st.session_state:
            db_info = {
                'db': st.session_state.selected_db,
                'collection_name': st.session_state.get('collection_name')
            }
            st.write(f"Using Session State DB Info: {db_info}")
        
        # Prepare the payload matching the QueryRequest structure
        payload = {
            "query": prompt,  # This is the actual question text
            "model": model,
            "top_k": 5,  # Default value for top_k
            "max_tokens": 1000
        }
        
        # Add collection name to payload if available
        if db_info and db_info.get('collection_name'):
            payload["collection_name"] = db_info.get('collection_name')
        elif 'collection_name' in st.session_state and st.session_state.collection_name:
            payload["collection_name"] = st.session_state.collection_name
        
        # Use the query API endpoint
        endpoint = QUERY_API_URL
        
        # Add database type as a query parameter if available
        if db_info and db_info.get('db'):
            endpoint = f"{QUERY_API_URL}?db_type={db_info.get('db')}"
        elif 'selected_db' in st.session_state and st.session_state.selected_db:
            endpoint = f"{QUERY_API_URL}?db_type={st.session_state.selected_db}"
        
        # Debug output
        st.write(f"API Endpoint: {endpoint}")
        st.write("Payload:", payload)
        
        # Calculate start time for processing time tracking
        start_time = datetime.now()
        
        # Make the API request
        response = requests.post(endpoint, json=payload)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Show response status
        st.write(f"API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract token usage information
            input_tokens = result.get("usage", {}).get("prompt_tokens", 0)
            output_tokens = result.get("usage", {}).get("completion_tokens", 0)
            
            # Estimate cost based on model
            cost = estimate_cost(model, input_tokens, output_tokens)
            
            # Update total token usage for the session
            st.session_state.total_token_usage["input_tokens"] += input_tokens
            st.session_state.total_token_usage["output_tokens"] += output_tokens
            st.session_state.total_token_usage["estimated_cost"] += cost
            
            return {
                "text": result.get("answer", "No answer returned from API"),  # Using answer instead of text_field
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost,
                "processing_time": processing_time,
                "model": model
            }
        else:
            error_text = f"API Error: {response.status_code} - {response.text}"
            st.error(error_text)
            # Return a fallback response to indicate failure but continue the conversation
            return {
                "text": f"I'm sorry, there was an error processing your request. {error_text}",  
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0,
                "processing_time": processing_time,
                "model": model
            }
    except Exception as e:
        error_details = traceback.format_exc()
        st.error(f"Error communicating with API: {str(e)}")
        st.error(f"Error details: {error_details}")
        # Return a fallback response to indicate failure but continue the conversation
        return {
            "text": f"I'm sorry, there was an error processing your request. Error: {str(e)}",
            "input_tokens": 0,
            "output_tokens": 0,
            "cost": 0,
            "processing_time": 0,
            "model": model
        }

def new_conversation():
    """Create a new conversation"""
    st.session_state.chat_history = []
    st.session_state.conversation_id = generate_unique_id()

def show_chat_ai():
    """Display the RAG interactive chat interface"""
    
    # Debug toggle to show/hide technical details
    if 'show_debug' not in st.session_state:
        st.session_state.show_debug = False
    
    # Debug container for technical messages
    debug_container = st.empty()
    
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
        
        /* Document selection */
        .document-selector {
            background-color: #f5f7fa;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 15px;
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
    
    # Get API backend URL from environment
    API_BACKEND_URL = os.getenv('API_BACKEND_URL', 'http://localhost:8003')

    # Show debug toggle
    st.sidebar.checkbox("Show Debug Info", key="show_debug_toggle", 
                        on_change=lambda: setattr(st.session_state, "show_debug", 
                                                  st.session_state.show_debug_toggle))

    # Add API testing button
    if st.button("🔄 Test API Connection"):
        QUERY_API_URL = os.getenv('QUERY_SERVICE_URL', 'http://localhost:8005/query')
        
        try:
            # Try to make a simple GET request
            base_url = QUERY_API_URL.split('/query')[0] if '/query' in QUERY_API_URL else QUERY_API_URL
            health_url = f"{base_url}/health"
            
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                st.success("API connection successful!")
            else:
                st.error(f"API returned status code: {response.status_code}")
                
        except Exception as e:
            st.error(f"API connection test failed: {str(e)}")
            st.error(f"Details: {traceback.format_exc()}")

    # Initialize session states
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
        
    if 'conversation_id' not in st.session_state:
        st.session_state.conversation_id = generate_unique_id()
    
    # Check Redis status
    redis_available = False
    try:
        if hasattr(redis_helper, 'REDIS_AVAILABLE'):
            redis_available = redis_helper.REDIS_AVAILABLE
            
            if redis_available:
                # Try to sync with Redis
                redis_helper.force_sync_session_with_redis()
                
                # Get database info
                db_info = redis_helper.get_db_info()
                
                if st.session_state.show_debug:
                    with debug_container.container():
                        st.write("Redis Status:", "Available")
                        st.write("Redis DB Info:", db_info)
                
                # Update session state if Redis has valid database info
                if db_info and db_info.get('db'):
                    st.session_state.selected_db = db_info.get('db')
                    st.session_state.collection_name = db_info.get('collection_name')
        else:
            if st.session_state.show_debug:
                with debug_container.container():
                    st.write("Redis Status: REDIS_AVAILABLE attribute not found")
    except Exception as e:
        if st.session_state.show_debug:
            with debug_container.container():
                st.write("Redis Error:", str(e))
    
    # Initialize database selection if not already set
    if 'selected_db' not in st.session_state:
        # Debug option: Force a default database for testing
        if st.session_state.show_debug:
            st.session_state.selected_db = "dummy_db"  # Uncomment to force a database for testing
        else:
            st.session_state.selected_db = None
    
    if 'collection_name' not in st.session_state:
        if st.session_state.show_debug:
            st.session_state.collection_name = "dummy_collection"  # Uncomment to force a collection for testing
        else:
            st.session_state.collection_name = None
    
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
    st.title("📚 RAG Interactive Chat")
    
    # Environment variables debug section
    if st.session_state.show_debug:
        with debug_container.container():
            st.subheader("Environment Variables")
            st.write(f"QUERY_API_URL: {os.getenv('QUERY_API_URL', 'Not set (using default)')}")
            st.write(f"API_BACKEND_URL: {os.getenv('API_BACKEND_URL', 'Not set (using default)')}")
    
    # Sidebar for model selection and token usage
    with st.sidebar:
        st.header("Model Settings")
        
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
        st.markdown("### Token Usage & Cost")
        
        # Show pricing for selected model
        model_pricing = {
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
        
        if llm_model_id in model_pricing:
            price_info = model_pricing[llm_model_id]
            st.info(f"**Pricing:** Input: ${price_info['input']}/1K tokens | Output: ${price_info['output']}/1K tokens")
            
        # Display current session usage metrics
        st.metric("Input Tokens", st.session_state.total_token_usage['input_tokens'])
        st.metric("Output Tokens", st.session_state.total_token_usage['output_tokens'])
        st.metric("Estimated Cost", f"${st.session_state.total_token_usage['estimated_cost']:.4f}")
        
        if st.button("Reset Usage Stats", key="reset_stats"):
            st.session_state.total_token_usage = {
                "input_tokens": 0,
                "output_tokens": 0,
                "estimated_cost": 0.0
            }
            st.success("Usage statistics have been reset")
            st.rerun()
        
        if st.button("New Chat", key="new_chat", use_container_width=True):
            new_conversation()
            st.rerun()
    
    # Main content area
    # Display current database connection status
    if st.session_state.selected_db:
        st.markdown(
            f"""
            <div class="document-selector">
                <p><strong>Current Database:</strong> {st.session_state.selected_db}
                {f" • Collection: {st.session_state.collection_name}" if st.session_state.collection_name else ""}</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        # Debug option to force a database connection for testing
        if st.session_state.show_debug:
            st.button("Force Database Connection (Debug)", on_click=lambda: setattr(st.session_state, "selected_db", "test_db"))
            
        st.info("No database connection found. Please ensure your application sets a database connection in the data parsing module first.")
    
    # Display chat messages
    st.markdown("### Chat")
    
    chat_container = st.container(height=400)
    
    with chat_container:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(
                    f"""
                    <div class="user-message">
                        <p>{message["content"]}</p>
                        <div class="message-metadata">{message.get("timestamp", "")}</div>
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
                
                # Display the message with token counts and cost
                st.markdown(
                    f"""
                    <div class="assistant-message">
                        <p>{message["content"]}</p>
                        <div class="message-metadata">
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
                        {message["content"]}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    
    # User input area
    st.markdown("### Ask a Question")
    
    # Debug container
    debug_msg_container = st.empty()
    
    user_input = st.text_input("", placeholder="Ask a question about your document...", key="user_question")
    
    col1, col2 = st.columns([6, 1])
    
    with col2:
        send_button = st.button("Send", key="send_question", use_container_width=True)
    
    # Process user input when send button is clicked
    if send_button and user_input:
        # Display debug information if enabled
        if st.session_state.show_debug:
            with debug_msg_container.container():
                st.write("Send button clicked!")
                st.write(f"User input: '{user_input}'")
                st.write(f"Model: {llm_model_id}")
                
                # Debug database connection
                st.write(f"Session DB: {st.session_state.get('selected_db')}")
                if hasattr(redis_helper, 'REDIS_AVAILABLE') and redis_helper.REDIS_AVAILABLE:
                    redis_helper.force_sync_session_with_redis()
                    db_info = redis_helper.get_db_info()
                    st.write(f"DB Info from Redis: {db_info}")
        
        # Check if we need to force a database connection for testing
        if st.session_state.show_debug and st.session_state.selected_db is None:
            st.session_state.selected_db = "debug_forced_db"
            st.session_state.collection_name = "debug_forced_collection"
            with debug_msg_container.container():
                st.write("FORCED DATABASE CONNECTION FOR DEBUGGING")
        
        # Add user message to chat history
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
        
        # Process the question with visual feedback
        with st.spinner("Generating response..."):
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
            else:
                # Add a failure message to let the user know something went wrong
                st.session_state.chat_history.append({
                    "role": "system",
                    "content": "Sorry, there was an error processing your request. Please try again.",
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                })
        
        # Clear the input field and refresh
        if "user_question" in st.session_state:
            del st.session_state.user_question
        st.rerun()

# Entry point for the Streamlit application
def main():
    # Set page config
    st.set_page_config(
        page_title="RAG Interactive Chat",
        page_icon="📚",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Display the chat interface
    show_chat_ai()
    
if __name__ == "__main__":
    main()