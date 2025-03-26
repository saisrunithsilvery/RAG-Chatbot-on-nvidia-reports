def get_all_markdown_folders():
    """
    Generate URLs for all NVIDIA quarterly report folders.
    
    Returns:
        list: List of folder URLs containing markdown files
    """
    # Using the correct region as specified in your sample URL
    base_url = "https://damg7245-nvidia-reports.s3.us-east-1.amazonaws.com/"
    prefix = "mistral-parsed/"
    folder_urls = []
    
    # Based on the folders shown in the screenshot
    quarters = [1, 2, 3, 4]
    years = [2020, 2021, 2022, 2023, 2024]
    
    for year in years:
        for quarter in quarters:
            # From your example URL, markdown files are in a subdirectory called "markdown"
            folder_path = f"{prefix}nvidia-q{quarter}-{year}/markdown/"
            full_url = base_url + folder_path
            folder_urls.append(full_url)
    
    return folder_urls

def check_markdown_file(folder_url, filename):
    """
    Check if a specific markdown file exists in a folder.
    
    Args:
        folder_url (str): URL of the folder
        filename (str): Name of the markdown file to check
        
    Returns:
        str or None: Full URL if file exists, None otherwise
    """
    import requests
    
    file_url = folder_url + filename
    try:
        response = requests.head(file_url, timeout=5)
        if response.status_code == 200:
            return file_url
        return None
    except:
        return None

def find_markdown_files():
    """
    Find markdown files in NVIDIA quarterly report folders.
    
    Returns:
        list: List of found markdown file URLs
    """
    import requests
    from concurrent.futures import ThreadPoolExecutor
    
    folder_urls = get_all_markdown_folders()
    markdown_urls = []
    
    # List of possible filenames to check
    # Since you mentioned one specific file as tmp1742846876.md
    # We'll try different tmp* patterns
    potential_filenames = [
        "tmp1742846876.md",  # Your example
        "report.md",
        "summary.md",
        "earnings.md",
        "transcript.md",
        "financials.md"
    ]
    
    # Check for the existence of common markdown files in each folder
    for folder_url in folder_urls:
        for filename in potential_filenames:
            file_url = check_markdown_file(folder_url, filename)
            if file_url:
                markdown_urls.append(file_url)
                # If we found one file in this folder, move to the next folder
                break
    
    return markdown_urls

# Example usage
if __name__ == "__main__":
    print("Generating URLs for NVIDIA quarterly report markdown files...")
    
    # Get folder URLs
    folder_urls = get_all_markdown_folders()
    print(f"Found {len(folder_urls)} potential folders")
    
    # Try to find markdown files
    markdown_files = find_markdown_files()
    
    if markdown_files:
        print(f"\nFound {len(markdown_files)} markdown files:")
        for url in markdown_files:
            print(url)
    else:
        print("\nCouldn't find any markdown files using common filenames.")
        print("You may need to:")
        print("1. Check the exact filenames manually in a web browser")
        print("2. Get the exact URLs from someone who knows them")
        
    print("\nAll potential folder URLs:")
    for url in folder_urls:
        print(url)