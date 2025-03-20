from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.utils.dates import days_ago
from airflow.models import Variable
from airflow.hooks.http_hook import HttpHook
from datetime import datetime, timedelta
import requests
import json
import os
import sys
sys.path.append('/opt/airflow')
import tempfile
import boto3
import logging
from rag.chunking import chunk_by_character_with_embeddings, chunk_by_tokens_with_embeddings, chunk_recursively_with_embeddings
from vectordb.chromadb import store_in_chroma
from vectordb.pinecone import store_in_pinecone


logger = logging.getLogger(__name__)

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

PARSER_SERVICE_URLS = {
    'docling': 'http://localhost:8001/',
    'mistral_ocr': 'http://localhost:8002/',  # Fixed typo in URL
    'opensource': 'http://assignment1-parser-service:8003/'
}

# Define supported chunking strategies
CHUNKING_STRATEGIES = {
    'character': chunk_by_character_with_embeddings,
    'token': chunk_by_tokens_with_embeddings,
    'recursive': chunk_recursively_with_embeddings
}

# Define supported vector databases
VECTOR_DBS = ['pinecone', 'chroma', 'milvus', 'qdrant']

# S3 configuration
S3_BUCKET = 'nvidia-quarterly-reports'
S3_REGION = 'us-east-1'

def get_s3_client():
    """Create and return an S3 client"""
    return boto3.client('s3',
                       region_name=S3_REGION,
                       aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
                       aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'))

def download_from_s3(s3_path, local_path):
    """Download a file from S3 to a local path"""
    s3_client = get_s3_client()
    bucket, key = s3_path.replace('s3://', '').split('/', 1)
    s3_client.download_file(bucket, key, local_path)
    return local_path

def upload_to_s3(local_path, s3_path):
    """Upload a file from a local path to S3"""
    s3_client = get_s3_client()
    bucket, key = s3_path.replace('s3://', '').split('/', 1)
    s3_client.upload_file(local_path, bucket, key)
    return s3_path

def process_request(**kwargs):
    """Process the DAG run configuration parameters and store them for later tasks"""
    ti = kwargs['ti']
    dag_run = kwargs['dag_run']
    
    # Extract parameters from dag_run.conf
    parser_type = dag_run.conf.get('parser_type', 'docling')
    chunking_strategy = dag_run.conf.get('chunking_strategy', 'recursive')  # Changed default to a valid strategy
    vector_db = dag_run.conf.get('vector_db', 'chroma')  # Changed default to a supported DB
    s3_folder = dag_run.conf.get('s3_folder', 'default_folder')
    quarter = dag_run.conf.get('quarter', 'Q1_2023')  # Added default quarter
    chunk_size = dag_run.conf.get('chunk_size', 1000)  # Added chunk size parameter
    chunk_overlap = dag_run.conf.get('chunk_overlap', 200)  # Added chunk overlap parameter
    
    # Construct the S3 file path
    input_file_path = f's3://{S3_BUCKET}/{s3_folder}/input.pdf'
    
    # Log the configuration
    logger.info(f"Processing request with configuration:")
    logger.info(f"- Parser Type: {parser_type}")
    logger.info(f"- Chunking Strategy: {chunking_strategy}")
    logger.info(f"- Vector DB: {vector_db}")
    logger.info(f"- S3 Folder: {s3_folder}")
    logger.info(f"- Quarter: {quarter}")
    logger.info(f"- Chunk Size: {chunk_size}")
    logger.info(f"- Chunk Overlap: {chunk_overlap}")
    logger.info(f"- Input File Path: {input_file_path}")
    
    # Validate parameters
    if parser_type not in PARSER_SERVICE_URLS:
        raise ValueError(f"Invalid parser type: {parser_type}. Supported types: {list(PARSER_SERVICE_URLS.keys())}")
    
    if chunking_strategy not in CHUNKING_STRATEGIES:
        raise ValueError(f"Invalid chunking strategy: {chunking_strategy}. Supported strategies: {list(CHUNKING_STRATEGIES.keys())}")
    
    if vector_db not in VECTOR_DBS:
        raise ValueError(f"Invalid vector DB: {vector_db}. Supported DBs: {VECTOR_DBS}")
    
    # Pass parameters to downstream tasks
    ti.xcom_push(key='parser_type', value=parser_type)
    ti.xcom_push(key='chunking_strategy', value=chunking_strategy)
    ti.xcom_push(key='vector_db', value=vector_db)
    ti.xcom_push(key='input_file_path', value=input_file_path)
    ti.xcom_push(key='quarter', value=quarter)
    ti.xcom_push(key='s3_folder', value=s3_folder)
    ti.xcom_push(key='chunk_size', value=chunk_size)
    ti.xcom_push(key='chunk_overlap', value=chunk_overlap)
    
    return "Request processed successfully"

def parse_document(**kwargs):
    """Send the document to the selected parser service"""
    ti = kwargs['ti']
    
    # Get parameters from previous task
    parser_type = ti.xcom_pull(task_ids='process_request', key='parser_type')
    input_file_path = ti.xcom_pull(task_ids='process_request', key='input_file_path')
    s3_folder = ti.xcom_pull(task_ids='process_request', key='s3_folder')
    
    parser_url = PARSER_SERVICE_URLS[parser_type]
    
    # Download from S3 to a local temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        local_input_path = tmp.name
    
    try:
        download_from_s3(input_file_path, local_input_path)
        logger.info(f"Downloaded input file to {local_input_path}")
        
        # Send request to parser service
        response = requests.post(
            parser_url,
            json={'input_file_path': local_input_path}
        )
        
        response.raise_for_status()
        parsed_data = response.json()
        
        # Get the output file path from the parser service response
        parsed_file_path = parsed_data.get('output_file_path')
        
        if not parsed_file_path:
            raise ValueError("No output file path returned from parser service")
        
        logger.info(f"Document parsed successfully: {parsed_file_path}")
        return parsed_file_path
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling parser service: {e}")
        raise
    except Exception as e:
        logger.error(f"Error in parse_document: {e}")
        raise
    finally:
        # Clean up the temporary file
        if os.path.exists(local_input_path):
            os.unlink(local_input_path)

def chunk_document(**kwargs):
    """Chunk the parsed document and generate embeddings"""
    ti = kwargs['ti']
    
    # Get parameters from previous tasks
    chunking_strategy = ti.xcom_pull(task_ids='process_request', key='chunking_strategy')
    parsed_file_path = ti.xcom_pull(task_ids='parse_document')
    quarter = ti.xcom_pull(task_ids='process_request', key='quarter')
    chunk_size = ti.xcom_pull(task_ids='process_request', key='chunk_size')
    chunk_overlap = ti.xcom_pull(task_ids='process_request', key='chunk_overlap')

    # Get the appropriate chunking function
    if chunking_strategy in CHUNKING_STRATEGIES:
        chunking_function = CHUNKING_STRATEGIES[chunking_strategy]
    else:
        raise ValueError(f"Invalid chunking strategy: {chunking_strategy}")
    
    try:
        # Add metadata for the chunks
        metadata = {
            "quarter": quarter,
            "source_file": parsed_file_path,
            "processing_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        # Apply chunking function with appropriate parameters
        embeddings = chunking_function(
            url=parsed_file_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            common_metadata=metadata
        )
        
        logger.info(f"Document chunked successfully into {len(embeddings)} chunks")
        
        # Save the file path and embeddings to XCom
        ti.xcom_push(key='chunked_file_path', value=parsed_file_path)
        ti.xcom_push(key='embeddings', value=embeddings)
        
        return parsed_file_path
        
    except Exception as e:
        logger.error(f"Error in chunk_document: {str(e)}")
        raise

def store_in_vector_db(**kwargs):
    """Send the chunked document to the selected vector DB service"""
    ti = kwargs['ti']
    
    # Get parameters from previous tasks
    vector_db = ti.xcom_pull(task_ids='process_request', key='vector_db')
    chunked_file_path = ti.xcom_pull(task_ids='chunk_document', key='chunked_file_path')
    quarter = ti.xcom_pull(task_ids='process_request', key='quarter')
    embeddings = ti.xcom_pull(task_ids='chunk_document', key='embeddings')
    
    # Ensure we have all required data
    if not chunked_file_path:
        chunked_file_path = ti.xcom_pull(task_ids='chunk_document')
    
    if not embeddings:
        logger.error("No embeddings found in XCom")
        raise ValueError("No embeddings found in XCom")
    
    # Store in the appropriate vector database
    logger.info(f"Storing {len(embeddings)} embeddings in {vector_db}")
    
    result = None
    
    try:
        if vector_db.lower() == 'pinecone':
            result = store_in_pinecone(embeddings, chunked_file_path, quarter)
        elif vector_db.lower() == 'chroma':
            result = store_in_chroma(embeddings, chunked_file_path, quarter)
        elif vector_db.lower() == 'milvus':
            result = store_in_milvus(embeddings, chunked_file_path, quarter)
        elif vector_db.lower() == 'qdrant':
            result = store_in_qdrant(embeddings, chunked_file_path, quarter)
        else:
            raise ValueError(f"Unsupported vector database: {vector_db}")
        
        # Store the result (collection/index name) for downstream tasks
        ti.xcom_push(key='vector_db_location', value=result)
        
        logger.info(f"Successfully stored embeddings in {vector_db} at {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error in store_in_vector_db: {str(e)}")
        raise
      
# Create the DAG
with DAG(
    'nvidia_rag_pipeline',
    default_args=default_args,
    description='RAG Pipeline for NVIDIA Quarterly Reports',
    schedule_interval=None,  # This DAG will be triggered externally
    start_date=days_ago(1),
    tags=['rag', 'nvidia'],
) as dag:

    start = DummyOperator(
        task_id='start',
    )
    
    process_request_task = PythonOperator(
        task_id='process_request',
        python_callable=process_request,
        provide_context=True,
    )
    
    parse_document_task = PythonOperator(
        task_id='parse_document',
        python_callable=parse_document,
        provide_context=True,
    )
    
    chunk_document_task = PythonOperator(
        task_id='chunk_document',
        python_callable=chunk_document,
        provide_context=True,
    )
    
    store_in_vector_db_task = PythonOperator(
        task_id='store_in_vector_db',
        python_callable=store_in_vector_db,
        provide_context=True,
    )
    
    end = DummyOperator(
        task_id='end',
    )
    
    # Define task dependencies
    start >> process_request_task >> parse_document_task >> chunk_document_task >> store_in_vector_db_task >> end