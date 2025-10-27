"""Pytest fixtures for testing with MinIO (S3-compatible storage).

This module provides fixtures to set up and tear down MinIO for integration tests.
MinIO provides a local S3-compatible object storage for testing.
"""

import pytest
import boto3
from botocore.exceptions import ClientError
import time
import os


@pytest.fixture(scope="session")
def minio_config():
    """MinIO connection configuration.
    
    Returns:
        dict: Configuration for connecting to MinIO
    """
    return {
        'endpoint_url': os.getenv('MINIO_ENDPOINT', 'http://localhost:9000'),
        'aws_access_key_id': os.getenv('MINIO_ACCESS_KEY', 'minioadmin'),
        'aws_secret_access_key': os.getenv('MINIO_SECRET_KEY', 'minioadmin'),
        'region_name': 'us-east-1'  # MinIO doesn't care, but boto3 requires it
    }


@pytest.fixture(scope="session")
def minio_client(minio_config):
    """Create boto3 S3 client connected to MinIO.
    
    Args:
        minio_config: MinIO configuration fixture
    
    Returns:
        boto3.client: S3 client connected to MinIO
    
    Raises:
        pytest.skip: If MinIO is not available
    """
    client = boto3.client('s3', **minio_config)
    
    # Check if MinIO is available
    try:
        client.list_buckets()
    except Exception as e:
        pytest.skip(f"MinIO not available: {e}")
    
    return client


@pytest.fixture
def minio_bucket(minio_client):
    """Create a temporary test bucket in MinIO.
    
    Args:
        minio_client: MinIO S3 client fixture
    
    Yields:
        str: Name of the created bucket
    
    The bucket is automatically cleaned up after the test.
    """
    bucket_name = f"test-bucket-{int(time.time())}"
    
    # Create bucket
    try:
        minio_client.create_bucket(Bucket=bucket_name)
    except ClientError as e:
        if e.response['Error']['Code'] != 'BucketAlreadyExists':
            raise
    
    yield bucket_name
    
    # Cleanup: delete all objects then bucket
    try:
        # List and delete all objects
        response = minio_client.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            objects = [{'Key': obj['Key']} for obj in response['Contents']]
            if objects:
                minio_client.delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': objects}
                )
        
        # Delete bucket
        minio_client.delete_bucket(Bucket=bucket_name)
    except Exception as e:
        print(f"Warning: Failed to cleanup bucket {bucket_name}: {e}")


@pytest.fixture
def s3_storage_config(minio_bucket, minio_config):
    """Storage configuration for S3 backend using MinIO.
    
    Args:
        minio_bucket: MinIO bucket fixture
        minio_config: MinIO configuration fixture
    
    Returns:
        dict: Configuration dict for StorageManager
    """
    return {
        'name': 'test-s3',
        'type': 's3',
        'bucket': minio_bucket,
        'endpoint_url': minio_config['endpoint_url'],
        'key': minio_config['aws_access_key_id'],
        'secret': minio_config['aws_secret_access_key'],
    }


@pytest.fixture
def storage_with_s3(s3_storage_config):
    """Create StorageManager configured with MinIO S3 backend.
    
    Args:
        s3_storage_config: S3 storage configuration fixture
    
    Returns:
        StorageManager: Configured storage manager with S3 backend
    """
    from genro_storage import StorageManager
    
    storage = StorageManager()
    storage.configure([s3_storage_config])
    
    return storage
