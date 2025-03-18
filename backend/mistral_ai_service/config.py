import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration
API_TITLE = "Document OCR API"
API_DESCRIPTION = "API for OCR processing with Mistral and S3 upload"
API_VERSION = "1.0.0"

# Mistral Configuration
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_OCR_MODEL = os.getenv("MISTRAL_OCR_MODEL", "mistral-ocr-latest")

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Temporary file storage
TEMP_UPLOAD_DIR = os.getenv("TEMP_UPLOAD_DIR", "temp_uploads")
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

# Max file size (in MB)
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 10))