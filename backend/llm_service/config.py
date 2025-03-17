# llm_service/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# GitHub model configuration
GITHUB_CONFIG = {
    "api_key": os.environ.get("GITHUB_TOKEN", ""),
    "base_url": "https://models.inference.ai.azure.com"
}

# Available models through GitHub
AVAILABLE_MODELS = [
    {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "provider": "GitHub",
        "context_window": 128000,
        "capabilities": ["text", "images", "tools"]
    }
]

# Model mapping for LiteLLM
MODEL_MAPPING = {
    "gpt-4o": "github/gpt-4o"
}

# Token pricing for cost calculation
MODEL_PRICING = {
    "gpt-4o": {"input": 0.01, "output": 0.03}
}





# import os

# # GitHub model configuration
# GITHUB_CONFIG = {
#     "api_key": os.environ.get("GITHUB_TOKEN"),
#     "base_url": "https://models.inference.ai.azure.com"
# }

# # Available models mapping - only GitHub models
# AVAILABLE_MODELS = {
#     "gpt-4o": "github/gpt-4o"  # GitHub's GPT-4o model
#     # You can add other GitHub models if they become available
# }

# # Token pricing for cost calculation
# MODEL_PRICING = {
#     "gpt-4o": {"input": 0.01, "output": 0.03}  # Adjust based on actual pricing
# }