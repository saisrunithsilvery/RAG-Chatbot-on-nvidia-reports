from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta
import boto3
import os
import sys
sys.path.append('/opt/airflow')
import tempfile
from rag.chunking import chunk_document

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
    'document_chunking_pipeline1',
    default_args=default_args,
    description='Pipeline to chunk documents and generate embeddings',
    schedule_interval=None,  # Set to None to disable scheduling - only trigger via API
    catchup=False,
)

def process_document(**kwargs):
    """
    Function to download file from S3 and process it using the chunk_document function
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
        
        # Process the document
        result, tmp_file_path = chunk_document(
            url=local_file_path,
            chunking_strategy=chunking_strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            model_name=model_name,
            document_metadata={
                'source_s3': f"s3://{s3_bucket}/{s3_key}",
                'processing_time': datetime.now().isoformat()
            }
        )
        
        # Push results to XCom
        ti.xcom_push(key='result_chunks', value=len(result))
        ti.xcom_push(key='tmp_file_path', value=tmp_file_path)
        ti.xcom_push(key='local_file_path', value=local_file_path)
        
        return tmp_file_path
        
    except Exception as e:
        print(f"Error processing document: {str(e)}")
        # Clean up in case of error
        if os.path.exists(local_file_path):
            os.remove(local_file_path)
        raise e

# Create task
chunk_document_task = PythonOperator(
    task_id='chunk_document_task',
    python_callable=process_document,
    provide_context=True,
    dag=dag,
)

# Cleanup task
def cleanup_temp_files(**kwargs):
    ti = kwargs['ti']
    local_file_path = ti.xcom_pull(task_ids='chunk_document_task', key='local_file_path')
    
    if local_file_path and os.path.exists(local_file_path):
        os.remove(local_file_path)
        
        # Remove parent directory if empty
        temp_dir = os.path.dirname(local_file_path)
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
    
    return "Cleanup complete"

cleanup_task = PythonOperator(
    task_id='cleanup_temp_files',
    python_callable=cleanup_temp_files,
    provide_context=True,
    dag=dag,
)

# Set dependencies
chunk_document_task >> cleanup_task