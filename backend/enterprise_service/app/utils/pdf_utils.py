# pdf_utils.py

import logging
from datetime import datetime
from pathlib import Path
import os

from adobe.pdfservices.operation.auth.service_principal_credentials import ServicePrincipalCredentials
from adobe.pdfservices.operation.exception.exceptions import ServiceApiException, ServiceUsageException, SdkException
from adobe.pdfservices.operation.pdf_services import PDFServices
from adobe.pdfservices.operation.pdf_services_media_type import PDFServicesMediaType
from adobe.pdfservices.operation.pdfjobs.jobs.extract_pdf_job import ExtractPDFJob
from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_element_type import ExtractElementType
from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_pdf_params import ExtractPDFParams
from adobe.pdfservices.operation.pdfjobs.params.extract_pdf.extract_renditions_element_type import ExtractRenditionsElementType

# from backend.app.utils.enterprise.handler_utils import process_zip  # Import the handler function

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_pdf_content(pdf_path: str, output_dir: str = "output") -> str:
    """Extract content from PDF using Adobe PDF Services API"""
    try:
        # Read PDF file
        with open(pdf_path, 'rb') as file:
            input_stream = file.read()

        # Get credentials
        credentials = ServicePrincipalCredentials(
            client_id=os.getenv('PDF_SERVICES_CLIENT_ID'),
            client_secret=os.getenv('PDF_SERVICES_CLIENT_SECRET')
        )

        # Initialize PDF services
        pdf_services = PDFServices(credentials=credentials)

        # Upload PDF
        input_asset = pdf_services.upload(
            input_stream=input_stream,
            mime_type=PDFServicesMediaType.PDF
        )

        # Set extraction parameters
        extract_params = ExtractPDFParams(
            elements_to_extract=[
                ExtractElementType.TEXT,
                ExtractElementType.TABLES
            ],
            elements_to_extract_renditions=[
                ExtractRenditionsElementType.TABLES,
                ExtractRenditionsElementType.FIGURES
            ]
        )

        # Create and submit job
        extract_job = ExtractPDFJob(
            input_asset=input_asset,
            extract_pdf_params=extract_params
        )

        # Get results
        location = pdf_services.submit(extract_job)
        from adobe.pdfservices.operation.pdfjobs.result.extract_pdf_result import ExtractPDFResult
        response = pdf_services.get_job_result(location, ExtractPDFResult)
        
        # Save ZIP file
        result_asset = response.get_result().get_resource()
        stream_asset = pdf_services.get_content(result_asset)
        
        # Ensure output directory exists
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        output_zip = output_path / f"extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        with open(output_zip, "wb") as f:
            f.write(stream_asset.get_input_stream())
        
        logger.info(f"Saved ZIP file to: {output_zip}")
        
        return str(output_zip)

    except (ServiceApiException, ServiceUsageException, SdkException) as e:
        logger.error(f"Error extracting PDF content: {str(e)}")
        raise

def main():
    try:
        # Set your PDF path here
        pdf_path = "./TestingDocs/main.pdf"  # Replace with your PDF path
        output_dir = "output"
        
        # Step 1: Extract PDF content to ZIP
        zip_path = extract_pdf_content(pdf_path, output_dir)
        logger.info(f"PDF extraction completed. ZIP file saved at: {zip_path}")
        
        # Step 2: Process the ZIP file using the imported handler
        process_zip(zip_path, output_dir)
        logger.info("Processing completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main()