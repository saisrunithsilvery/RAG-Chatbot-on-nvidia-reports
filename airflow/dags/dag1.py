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
import tempfile
import boto3
import logging
from rag.chunking import chunk_by_character_with_embeddings, chunk_by_tokens_with_embeddings, chunk_recursively_with_embeddings


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
    'mistral_ocr': 'http://locslhost:8002/',
    'opensource': 'http://assignment1-parser-service:8003/'
}

CHUNK_TYPES = {
    'chunk_by_character_with_embeddings': 'chunk_by_character_with_embeddings',
    'chunk_by_tokens_with_embeddings': 'chunk_by_tokens_with_embeddings',
    'chunk_by_tokens_with_embeddings': 'chunk_by_tokens_with_embeddings'
}



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
    chunking_strategy = dag_run.conf.get('chunking_strategy', 'semantic_sections')
    vector_db = dag_run.conf.get('vector_db', 'manual')
    s3_folder = dag_run.conf.get('s3_folder', 'default_folder')
    quarter = dag_run.conf.get('quarter', 'all')
    
    # Construct the S3 file path
    input_file_path = f's3://{S3_BUCKET}/{s3_folder}/input.pdf'
    
    # Log the configuration
    logger.info(f"Processing request with configuration:")
    logger.info(f"- Parser Type: {parser_type}")
    logger.info(f"- Chunking Strategy: {chunking_strategy}")
    logger.info(f"- Vector DB: {vector_db}")
    logger.info(f"- S3 Folder: {s3_folder}")
    logger.info(f"- Quarter: {quarter}")
    logger.info(f"- Input File Path: {input_file_path}")
    
    # # Validate parameters
    # if parser_type not in PARSER_SERVICE_URLS:
    #     raise ValueError(f"Invalid parser type: {parser_type}")
    
    # if vector_db not in VECTOR_DB_SERVICE_URLS:
    #     raise ValueError(f"Invalid vector DB: {vector_db}")
    
    # Pass parameters to downstream tasks
    ti.xcom_push(key='parser_type', value=parser_type)
    ti.xcom_push(key='chunking_strategy', value=chunking_strategy)
    ti.xcom_push(key='vector_db', value=vector_db)
    ti.xcom_push(key='input_file_path', value=input_file_path)
    ti.xcom_push(key='quarter', value=quarter)
    ti.xcom_push(key='s3_folder', value=s3_folder)
    
    return "Request processed successfully"

def parse_document(**kwargs):
    """Send the document to the selected parser service"""
    ti = kwargs['ti']
    
    # Get parameters from previous task
    parser_type = ti.xcom_pull(task_ids='process_request', key='parser_type')
    input_file_path = ti.xcom_pull(task_ids='process_request', key='input_file_path')
    s3_folder = ti.xcom_pull(task_ids='process_request', key='s3_folder')
    
    parser_url = PARSER_SERVICE_URLS[parser_type]
    
    # Send request to parser service
    try:
        response = requests.post(
            parser_url,
            json={'input_file_path': s3_folder}
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

def chunk_document(**kwargs):
    """Send the parsed document to the chunking service"""
    ti = kwargs['ti']
    
    # Get parameters from previous tasks
    chunking_strategy = ti.xcom_pull(task_ids='process_request', key='chunking_strategy')
    parsed_file_path = ti.xcom_pull(task_ids='parse_document')
    quarter = ti.xcom_pull(task_ids='process_request', key='quarter')
    
   
    if chunking_strategy in CHUNK_TYPES:
        chunking_function = CHUNK_TYPES[chunking_strategy]

def store_in_vector_db(**kwargs):
    """Send the chunked document to the selected vector DB service"""
    ti = kwargs['ti']
    
    # Get parameters from previous tasks
    vector_db = ti.xcom_pull(task_ids='process_request', key='vector_db')
    chunked_file_path = ti.xcom_pull(task_ids='chunk_document')
    quarter = ti.xcom_pull(task_ids='process_request', key='quarter')
    
    vector_db_url = VECTOR_DB_SERVICE_URLS[vector_db]
    
    # Send request to vector DB service
    try:
        response = requests.post(
            vector_db_url,
            json={
                'input_file_path': chunked_file_path,
                'quarter': quarter
            }
        )
        
        response.raise_for_status()
        stored_data = response.json()
        
        # Get the index ID or other reference from the vector DB service response
        index_reference = stored_data.get('index_reference')
        
        if not index_reference:
            raise ValueError("No index reference returned from vector DB service")
        
        logger.info(f"Document stored in vector DB successfully: {index_reference}")
        return index_reference
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling vector DB service: {e}")
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