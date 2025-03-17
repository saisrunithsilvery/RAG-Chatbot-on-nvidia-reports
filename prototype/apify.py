import os
import requests
import json
from urllib.parse import urljoin
from apify_client import ApifyClient
import markdown
import BeautifulSoup

# Initialize Apify client (Replace 'your_apify_token' with your actual token)
apify_client = ApifyClient("apify_api_TKJgbSjXw7wz9Im6i970h9fwfN5apA3Mmrht")

def scrape_data(url):
    run_input = {
        "startUrls": [{"url": url}],
        "globs": ["**/*"],
        "includeUrlPatterns": [".*"],
        "pageFunction": "async function pageFunction({ request, $, body }) { return { title: $(\"title\").text(), html: body }; }",
    }
    
    # Run the Apify Web Scraper
    run = apify_client.actor("apify/web-scraper").call(run_input=run_input)
    
    # Get dataset ID and fetch results
    dataset_id = run["defaultDatasetId"]
    dataset_items = apify_client.dataset(dataset_id).list_items().items
    
    content = []
    
    for item in dataset_items:
        soup = BeautifulSoup(item["html"], 'html.parser')
        
        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'table', 'img']):
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                content.append({'type': 'heading', 'text': element.get_text().strip()})
            elif element.name == 'p':
                content.append({'type': 'paragraph', 'text': element.get_text().strip()})
            elif element.name == 'table':
                table_data = [[cell.get_text().strip() for cell in row.find_all(['td', 'th'])] for row in element.find_all('tr')]
                content.append({'type': 'table', 'data': table_data})
            elif element.name == 'img':
                img_url = element.get('src')
                if img_url:
                    img_url = urljoin(url, img_url)  # Ensure absolute URL
                    img_extension = os.path.splitext(img_url.split("?")[0])[1].lower()
                    if img_extension not in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg"]:
                        img_extension = ".jpg"  # Default to .jpg if format is unknown
                    img_data = requests.get(img_url).content
                    img_folder = "scraped_images"
                    os.makedirs(img_folder, exist_ok=True)
                    img_name = f"{img_folder}/image_{len(content)+1}{img_extension}"
                    with open(img_name, 'wb') as f:
                        f.write(img_data)
                    content.append({'type': 'image', 'path': img_name})
    
    return content

# Function to save data in Markdown format
def save_to_md(content, output_file):
    md_content = "# Scraped Data\n\n"
    
    for item in content:
        if item['type'] == 'heading':
            md_content += f"## {item['text']}\n\n"
        elif item['type'] == 'paragraph':
            md_content += f"{item['text']}\n\n"
        elif item['type'] == 'table':
            for row in item['data']:
                md_content += " | ".join(row) + "\n"
            md_content += "\n"
        elif item['type'] == 'image':
            md_content += f"![Image]({item['path']})\n\n"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)

# URL to scrape
url = "https://en.wikipedia.org/wiki/Northeastern_University"  # Replace with actual URL
content = scrape_data(url)
save_to_md(content, "scraped_data.md")

print("Scraping completed. Data saved to scraped_data.md")
