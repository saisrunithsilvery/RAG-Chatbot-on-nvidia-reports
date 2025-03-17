#!/bin/bash

# Exit on error
set -e

# Configuration
ENTERPRISE_PORT=8000
OPENSOURCE_PORT=8001
LLM_PORT=8002
FRONTEND_PORT=8502
REDIS_PORT=6379

# Function to create and activate virtual environment
setup_venv() {
    local dir=$1
    echo "Setting up virtual environment in $dir"
    cd "$dir"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
}

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        echo "Port $port is already in use. Attempting to free it..."
        sudo kill -9 $(lsof -t -i:$port) || true
        sleep 2
    fi
}

# Function to install and start Redis
setup_redis() {
    echo "Installing Redis..."
    sudo apt update
    sudo apt install -y redis-server
    
    # Check if Redis port is in use
    check_port $REDIS_PORT
    
    echo "Starting Redis server..."
    redis-server --daemonize yes
    sleep 2
    
    # Verify Redis is running
    if redis-cli ping | grep -q "PONG"; then
        echo "Redis server is running successfully"
    else
        echo "Failed to start Redis server"
        exit 1
    fi
}

# Function to create .env file for LLM service
create_llm_env() {
    local env_file="backend/llm_service/.env"
    echo "Creating .env file for LLM service at $env_file"
    
    cat > "$env_file" << EOF
# OpenAI Configuration
OPENAI_API_KEY=""

# Anthropic Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Google Configuration
GOOGLE_API_KEY=""

# DeepSeek Configuration
DEEPSEEK_API_KEY=sk-""

# xAI Configuration (for Grok models)
XAI_API_KEY=your_xai_api_key_here
EOF

    echo "Created .env file for LLM service. Please update with your actual API keys."
}

# Function to start a service
start_service() {
    local service=$1
    local port=$2
    echo "Starting $service service on port $port"
    cd "backend/${service}_service"
    setup_venv .
    
    if [ "$service" = "enterprise" ]; then
        # Enterprise-specific environment variables
        export PDF_SERVICES_CLIENT_ID=${PDF_SERVICES_CLIENT_ID:-"YOUR_CLIENT_ID"}
        export PDF_SERVICES_CLIENT_SECRET=${PDF_SERVICES_CLIENT_SECRET:-"YOUR_CLIENT_SECRET"}
    fi
    
    if [ "$service" = "llm" ]; then
        # Create .env file if it doesn't exist
        if [ ! -f ".env" ]; then
            create_llm_env
        fi
    fi
    
    # Common AWS credentials
    export AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-"YOUR_ACCESS_KEY"}
    export AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-"YOUR_SECRET_KEY"}
    
    # Check and clear port if needed
    check_port $port
    
    echo "Starting uvicorn for $service service on port $port"
    uvicorn main:app --reload --port $port &
    sleep 5  # Wait for service to start
}

main() {
    # Install system dependencies
    echo "Updating system and installing dependencies..."
    sudo apt update
    sudo apt install -y python3 python3-pip lsof
    
    # Install and start Redis
    setup_redis
    
    # Store initial directory
    BASE_DIR=$(pwd)
    
    # Start backend services with different ports
    start_service "enterprise" $ENTERPRISE_PORT
    cd "$BASE_DIR"
    start_service "opensource" $OPENSOURCE_PORT
    cd "$BASE_DIR"
    start_service "llm" $LLM_PORT
    
    # Check and clear frontend port if needed
    check_port $FRONTEND_PORT
    
    # Start frontend
    echo "Starting frontend on port $FRONTEND_PORT..."
    cd "$BASE_DIR/frontend"
    setup_venv .
    streamlit run streamlit_app.py --server.port $FRONTEND_PORT
}

# Cleanup function
cleanup() {
    echo "Cleaning up processes..."
    pkill -f "uvicorn.*:$ENTERPRISE_PORT" || true
    pkill -f "uvicorn.*:$OPENSOURCE_PORT" || true
    pkill -f "uvicorn.*:$LLM_PORT" || true
    pkill -f "streamlit.*:$FRONTEND_PORT" || true
    redis-cli shutdown || true
}

# Set up trap for cleanup on script exit
trap cleanup EXIT

main