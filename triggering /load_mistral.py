import requests
import logging
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_s3_urls_with_mistral(s3_urls: List[str]) -> List[Dict]:
    """
    Process a list of S3 URLs with Mistral AI one by one.
    
    Args:
        s3_urls: List of S3 URLs to process
        mistral_api_key: Mistral AI API key
        
    Returns:
        List of processing results (success/failure) for each URL
    """
    results = []
    
    for url in s3_urls:
        logger.info(f"Processing URL: {url}")
        
        try:
            # Call Mistral API
            response = call_mistral_api(url)
            
            if response and 'choices' in response:
                results.append({
                    "url": url,
                    "status": "success",
                    "response": response
                })
                logger.info(f"Successfully processed URL: {url}")
            else:
                results.append({
                    "url": url,
                    "status": "error",
                    "error": "Invalid response from Mistral API"
                })
                logger.error(f"Failed to process URL: {url} - Invalid response")
                
        except Exception as e:
            results.append({
                "url": url,
                "status": "error", 
                "error": str(e)
            })
            logger.error(f"Error processing URL {url}: {str(e)}")
    
    return results

def call_mistral_api(file_url: str) -> Dict:
    """
    Call Mistral AI API with a file URL.
    
    Args:
        file_url: URL to the PDF file
        api_key: Mistral API key
    
    Returns:
        The response from Mistral API
    """
    mistral_endpoint = "http://0.0.0.0:8004/ocr/extract-pdf/mistral_ai"
    
    
    
    payload = {
        "s3_url": file_url   
    }
    
    response = requests.post(mistral_endpoint, json=payload)
    response.raise_for_status()
    return response.json()

# Example usage
if __name__ == "__main__":
    # Example list of S3 URLs
    s3_urls = [
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q1-2020.pdf",
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q1-2021.pdf",
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q1-2022.pdf",
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q1-2023.pdf",
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q1-2024.pdf",
    
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q2-2020.pdf",
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q2-2021.pdf",
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q2-2022.pdf",
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q2-2023.pdf",
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q2-2024.pdf",
    
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q3-2020.pdf",
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q3-2021.pdf",
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q3-2022.pdf",
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q3-2023.pdf",
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q3-2024.pdf",
    
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q4-2020.pdf",
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q4-2021.pdf",
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q4-2022.pdf",
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q4-2023.pdf",
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q4-2024.pdf",
    "https://damg7245-nvidia-reports.s3.amazonaws.com/raw_reports/nvidia-q4-2025.pdf"
]
    
    # Your Mistral API key
   
    
    # Process URLs
    results = process_s3_urls_with_mistral(s3_urls)
    
    # Print summary
    print(f"Total URLs: {len(results)}")
    print(f"Successful: {sum(1 for r in results if r['status'] == 'success')}")
    print(f"Failed: {sum(1 for r in results if r['status'] == 'error')}")