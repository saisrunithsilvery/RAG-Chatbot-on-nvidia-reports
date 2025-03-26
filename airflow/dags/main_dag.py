from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import boto3
import os
import sys
sys.path.append('/opt/airflow')
import tempfile
from rag.chunking import chunk_document
from vectordb.chromadb import load_chunks_into_chroma
from vectordb.nonvector import load_chunks_into_faiss
from vectordb.pinecone import load_chunks_into_pinecone
import re

# Define default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 3, 20),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define the DAG
dag = DAG(
    'document_chunking_pipeline',
    default_args=default_args,
    description='Pipeline to chunk documents and load into vector database',
    schedule_interval=None,  # Set to None to disable scheduling - only trigger via API
    catchup=False,
)

def process_document(**kwargs):
    """
    Function to download file from S3 and prepare it for chunking
    """
    ti = kwargs['ti']
    dag_run = kwargs.get('dag_run')
    
    # Get parameters from the API call
    conf = dag_run.conf if dag_run and dag_run.conf else {}
    
    # Extract parameters with defaults
    s3_bucket = conf.get('s3_bucket')
    s3_key = conf.get('s3_key')
    chunking_strategy = conf.get('chunking_strategy', 'recursive')
    vectordb = conf.get('vectordb','chromadb')
    
    # Get collection name for ChromaDB
    collection_name = conf.get('collection_name', 'nvidia_colllection')

    ##getting the year and quarter from the s3_key
    match = re.search(r"(q\d{1,2})-(\d{4})", s3_key)

    if match: 
        quarter = match.group(1)  # e.g., "q1"
        year = match.group(2)     


    
    # Validate required parameters
    if not s3_bucket or not s3_key:
        raise ValueError("Missing required parameters: s3_bucket and s3_key")
    
    # Create a temporary directory to store the downloaded file
    temp_dir = tempfile.mkdtemp()
    local_filename = os.path.basename(s3_key)
    print(f"This is my debug message: {local_filename}")
    print(f"This is my debug message: {temp_dir}")
    local_file_path = os.path.join(temp_dir, local_filename)
    
    # Connect to S3 using boto3
    print(f"Connecting to S3 and downloading s3://{s3_bucket}/{s3_key}")
    s3_client = boto3.client('s3')
    
    try:
        # Download file from S3
        s3_client.download_file(s3_bucket, s3_key, local_file_path)
        print(f"Successfully downloaded to {local_file_path}")
        
        # Push parameters to XCom for the chunking task
        ti.xcom_push(key='file_path', value=local_file_path)
        ti.xcom_push(key='chunk_strategy', value=chunking_strategy)
        ti.xcom_push(key='collection_name', value=collection_name)
        ti.xcom_push(key='chroma_persist_dir', value=conf.get('chroma_persist_dir', './chroma_db'))
        ti.xcom_push(key='vectordb', value=vectordb)
        ti.xcom_push(key='s3_key', value=s3_key)
        ti.xcom_push(key='year', value=year)
        ti.xcom_push(key='quarter', value=quarter)
        return local_file_path
        
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        # Clean up in case of error
        if os.path.exists(local_file_path):
            os.remove(local_file_path)
        raise e
    
def airflow_chunk_document(**kwargs):
    """Function to be used in Airflow DAG"""
    ti = kwargs['ti']
    
    # Get parameters from previous task - FIXED TASK ID
    file_path = ti.xcom_pull(task_ids='process_document_task', key='file_path')
    print(f"This is my debug message: {file_path}")
    chunk_strategy = ti.xcom_pull(task_ids='process_document_task', key='chunk_strategy')
    
    # Ensure default values if not provided
    if not chunk_strategy:
        chunk_strategy = "recursive"
    
    # Generate chunks
    print(f"Chunking document: {file_path}")
    chunks, tmp_file = chunk_document(
            url=file_path,
            chunking_strategy=chunk_strategy
        )
    
    # Push chunks to XCom for next task (optional, but could be useful)
    # Note: XCom might have size limitations for large chunk sets
    # ti.xcom_push(key='chunks', value=chunks)
    
    # Return the path to the temporary file for next task
    return tmp_file
def load_to_vector_db(**kwargs):
    """
    Function to load chunked documents into ChromaDB
    """
    ti = kwargs['ti']
    
    # Get data from previous task - FIXED TASK IDs
    tmp_file_path = ti.xcom_pull(task_ids='chunk_document_task')
    collection_name = ti.xcom_pull(task_ids='process_document_task', key='collection_name')
    chroma_persist_dir = ti.xcom_pull(task_ids='process_document_task', key='chroma_persist_dir')
    vectordb = ti.xcom_pull(task_ids='process_document_task', key='vectordb')
    year = ti.xcom_pull(task_ids='process_document_task', key='year')
    quarter = ti.xcom_pull(task_ids='process_document_task', key='quarter')
    chunk_strategy = ti.xcom_pull(task_ids='process_document_task', key='chunk_strategy')
    if not tmp_file_path:
        raise ValueError("No temporary file path found from previous task")
    
    try:
        # Choose vector database based on configuration
        if vectordb.lower() == "chromadb":
            print(f"Loading chunks into ChromaDB collection: {collection_name}")
            collection = load_chunks_into_chroma(
                tmp_path=tmp_file_path,
                collection_name=collection_name,
                persist_directory=chroma_persist_dir,
            )
        elif vectordb.lower() == "faiss":
            collection = load_chunks_into_faiss(
                tmp_path=tmp_file_path,
                index_name=collection_name,
                persist_directory="./faiss_index"
            )
        elif vectordb.lower() == "pinecone":
            print(f"Loading chunks into Pinecone collection: {collection_name}")
            collection = load_chunks_into_pinecone(
                tmp_path=tmp_file_path,
                collection_name=collection_name,
                year=year,
                quarter=quarter,
                chunk_strategy=chunk_strategy

            )    
        else:
            raise ValueError(f"Unsupported vector database: {vectordb}")
        
        # Push collection info to XCom
        ti.xcom_push(key='collection_loaded', value=True)
        ti.xcom_push(key='collection_name', value=collection_name)
        ti.xcom_push(key='vectordb_used', value=vectordb.lower())
        
        return collection_name
    
    except Exception as e:
        print(f"Error loading chunks into DB: {str(e)}")
        raise e

def cleanup_temp_files(**kwargs):
    """
    Function to clean up temporary files after processing
    """
    ti = kwargs['ti']
    local_file_path = ti.xcom_pull(task_ids='process_document_task', key='file_path')
    tmp_file_path = ti.xcom_pull(task_ids='chunk_document_task')
    
    files_to_cleanup = []
    if local_file_path and os.path.exists(local_file_path):
        files_to_cleanup.append(local_file_path)
    
    if tmp_file_path and os.path.exists(tmp_file_path):
        files_to_cleanup.append(tmp_file_path)
    
    for file_path in files_to_cleanup:
        try:
            os.remove(file_path)
            print(f"Removed temporary file: {file_path}")
        except Exception as e:
            print(f"Error removing file {file_path}: {str(e)}")
    
    # Remove parent directories if empty
    dirs_to_check = set()
    for file_path in files_to_cleanup:
        dirs_to_check.add(os.path.dirname(file_path))
    
    for dir_path in dirs_to_check:
        if os.path.exists(dir_path) and not os.listdir(dir_path):
            try:
                os.rmdir(dir_path)
                print(f"Removed empty directory: {dir_path}")
            except Exception as e:
                print(f"Error removing directory {dir_path}: {str(e)}")
    
    return "Cleanup complete"

# Create tasks
process_document_task = PythonOperator(
    task_id='process_document_task',
    python_callable=process_document,
    provide_context=True,
    dag=dag,
)

chunk_document_task = PythonOperator(
    task_id='chunk_document_task',
    python_callable=airflow_chunk_document,
    provide_context=True,
    dag=dag,
)

load_to_chroma_task = PythonOperator(
    task_id='load_to_chroma_task',
    python_callable=load_to_vector_db,
    provide_context=True,
    dag=dag,
)

cleanup_task = PythonOperator(
    task_id='cleanup_temp_files',
    python_callable=cleanup_temp_files,
    provide_context=True,
    dag=dag,
)

# Set dependencies - execute in sequence
process_document_task >> chunk_document_task >> load_to_chroma_task >> cleanup_task
