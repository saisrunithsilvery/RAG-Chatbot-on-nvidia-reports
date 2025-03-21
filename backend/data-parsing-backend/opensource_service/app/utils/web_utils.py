import requests
from pathlib import Path

def web_scrape(url):
    """Fetch HTML content from a URL using Jina API and save it to a file."""
    direct_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
   
    # Direct request to get raw HTML content
    response = requests.get(url, headers=direct_headers)
    response.raise_for_status()
    html_content = response.text

    output_dir = "output"
    # Save raw HTML to a file
    html_path = Path(output_dir) / "website.html"
    html_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

        
    return html_path