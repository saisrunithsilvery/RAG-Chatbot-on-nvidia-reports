import json
import os
import requests
from pathlib import Path
from urllib.parse import urlparse

def download_image(url, images_dir):
    """Download image from URL and save to images directory"""
    try:
        # Create a valid filename from the URL
        filename = os.path.basename(urlparse(url).path)
        if not filename:
            filename = f"image_{hash(url)}.jpg"
        
        filepath = os.path.join(images_dir, filename)
        
        # Don't download if image already exists
        if os.path.exists(filepath):
            return filepath

        response = requests.get(url)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
            
        return filepath
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
        return None

def convert_analyze_to_markdown(analyze_data, images_dir):
    """Convert Analyze API output to Markdown"""
    md_content = []
    
    # Add title
    if 'title' in analyze_data:
        md_content.append(f"# {analyze_data['title']}\n")
    
    # Process objects
    for obj in analyze_data.get('objects', []):
        # Add images
        for img in obj.get('images', []):
            if img.get('url'):
                local_path = download_image(img['url'], images_dir)
                if local_path:
                    title = img.get('title', 'Image')
                    md_content.append(f"![{title}](images/{os.path.basename(local_path)})\n")
                    if title:
                        md_content.append(f"*{title}*\n")
                    md_content.append("\n")
        
        # Add text content
        if 'text' in obj:
            md_content.append(obj['text'] + "\n\n")
    
    return "\n".join(md_content)



def main():
    # Create images directory if it doesn't exist
    images_dir = 'images'
    Path(images_dir).mkdir(parents=True, exist_ok=True)
    
   
    # Process Analyze API output
    with open('output/page_content.json', 'r', encoding='utf-8') as f:
        analyze_data = json.load(f)
    analyze_md = convert_analyze_to_markdown(analyze_data, images_dir)

    with open('output/analyze_output.md', 'w', encoding='utf-8') as f:
        f.write(analyze_md)
    
   
if __name__ == "__main__":
    main()