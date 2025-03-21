from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import boto3
import os
import sys
sys.path.append('/opt/airflow')
import tempfile
from rag.chunking import chunk_document, airflow_chunk_document
from rag.vector_db import load_chunks_into_chroma

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
    chunk_size = int(conf.get('chunk_size', 1000))
    chunk_overlap = int(conf.get('chunk_overlap', 200))
    model_name = conf.get('model_name', 'sentence-transformers/all-MiniLM-L6-v2')
    min_chunk_size = int(conf.get('min_chunk_size', 50))
    quarter = conf.get('quarter', datetime.now().strftime('%Y-Q%q'))
    
    # Get collection name for ChromaDB
    collection_name = conf.get('collection_name', f"collection_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    # Validate required parameters
    if not s3_bucket or not s3_key:
        raise ValueError("Missing required parameters: s3_bucket and s3_key")
    
    # Create a temporary directory to store the downloaded file
    temp_dir = tempfile.mkdtemp()
    local_filename = os.path.basename(s3_key)
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
        ti.xcom_push(key='chunk_size', value=chunk_size)
        ti.xcom_push(key='chunk_overlap', value=chunk_overlap)
        ti.xcom_push(key='model_name', value=model_name)
        ti.xcom_push(key='quarter', value=quarter)
        ti.xcom_push(key='min_chunk_size', value=min_chunk_size)
        ti.xcom_push(key='collection_name', value=collection_name)
        ti.xcom_push(key='chroma_persist_dir', value=conf.get('chroma_persist_dir', './chroma_db'))
        
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
    
    # Get parameters from previous task
    file_path = ti.xcom_pull(task_ids='process_request', key='file_path')
    chunk_strategy = ti.xcom_pull(task_ids='process_request', key='chunk_strategy')
    chunk_size = ti.xcom_pull(task_ids='process_request', key='chunk_size')
    chunk_overlap = ti.xcom_pull(task_ids='process_request', key='chunk_overlap')
    quarter = ti.xcom_pull(task_ids='process_request', key='quarter')
    min_chunk_size = ti.xcom_pull(task_ids='process_request', key='min_chunk_size', default=50)
    
    # Ensure default values if not provided
    if not chunk_strategy:
        chunk_strategy = "recursive"
    if not chunk_size:
        chunk_size = 1000
    if not chunk_overlap:
        chunk_overlap = 200
    
    # Create document metadata
    metadata = {
        "quarter": quarter,
        "processing_date": datetime.now().strftime("%Y-%m-%d")
    }
    
    # Generate embeddings
    embeddings, tmp_file = chunk_document(
        file_path,
        chunking_strategy=chunk_strategy,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        document_metadata=metadata,
        min_chunk_size=min_chunk_size
    )
    
    # Push embeddings to XCom for next task
    ti.xcom_push(key='embeddings', value=embeddings)
    
    # Return the path to the temporary file for next task
    return tmp_file    

def load_to_vector_db(**kwargs):
    """
    Function to load chunked documents into ChromaDB
    """
    ti = kwargs['ti']
    
    # Get data from previous task
    tmp_file_path = ti.xcom_pull(task_ids='chunk_document_task')
    collection_name = ti.xcom_pull(task_ids='process_document_task', key='collection_name')
    chroma_persist_dir = ti.xcom_pull(task_ids='process_document_task', key='chroma_persist_dir')
    
    if not tmp_file_path:
        raise ValueError("No temporary file path found from previous task")
    
    try:
        # Load chunks into ChromaDB
        collection = load_chunks_into_chroma(
            tmp_path=tmp_file_path,
            collection_name=collection_name,
            persist_directory=chroma_persist_dir,
            embedding_function_name="none"  # Use pre-computed embeddings
        )
        
        # Push collection info to XCom
        ti.xcom_push(key='collection_loaded', value=True)
        ti.xcom_push(key='collection_name', value=collection_name)
        
        return collection_name
    
    except Exception as e:
        print(f"Error loading chunks into ChromaDB: {str(e)}")
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