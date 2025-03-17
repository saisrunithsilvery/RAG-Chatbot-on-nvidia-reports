import requests
from pathlib import Path
import logging
import re
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(level=logging.INFO)
_log = logging.getLogger(__name__)


# Web scraping utility functions
def web_scraping_enterprise(url):
    """Fetch Markdown content from a URL using Jina API and save it to a file."""
    base_url = "https://r.jina.ai/"
    api_key = "jina_ad2a179a517a40f991ba1a2de1a1f925YS64rXRYkejV3OIHif7D7sA-U0R1"
    output_dir = "test_output"
    jina_headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "text/markdown"
    }
    
    params = {
        "x-respond-with": "markdown",  # Ensure Jina API returns Markdown
        "token_budget": 200000,
        "timeout": 10
    }

    try:
        # Request processed Markdown from Jina AI
        jina_response = requests.get(
            f"{base_url}{url}",
            headers=jina_headers,
            params=params
        )
        jina_response.raise_for_status()
        
        # Extract Markdown content
        markdown_content = jina_response.text
        
        # Save Markdown content to file
        md_path = Path.cwd() / "test_output" / "content.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        
        _log.info(f"Markdown content fetched and saved to: {md_path}")
        
        return md_path

    except requests.exceptions.RequestException as e:
        _log.error(f"Failed to fetch {url}. Error: {str(e)}")
        raise ValueError(f"Failed to fetch {url}. Error: {str(e)}")