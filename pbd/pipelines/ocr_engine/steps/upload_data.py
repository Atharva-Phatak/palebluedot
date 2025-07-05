"""
Data Storage Step for OCR Engine

This module provides a ZenML step for storing OCR extraction results as Parquet files in MinIO.
It handles serialization of Hugging Face Datasets and robust upload to object storage.

Functions:
    store_extracted_texts_to_minio(dataset, bucket_name, minio_endpoint, filename, secure=False):
        ZenML step to store OCR results in MinIO as Parquet files.
"""

import os
import tempfile

from datasets import Dataset
from minio import Minio


def store_extracted_texts_to_minio(
    dataset: Dataset | list,
    bucket_name: str,
    minio_endpoint: str,
    filename: str,
    secure=False,
):
    """
    ZenML step to store OCR extraction results as Parquet files in MinIO using the MinIO client.

    Args:
        dataset (Dataset): Hugging Face Dataset containing OCR results, typically with keys like 'image_path' and 'extracted_text'.
        bucket_name (str): MinIO bucket name where the file will be stored.
        minio_endpoint (str): MinIO server endpoint (e.g., "localhost:9000").
        filename (str): Filename (without extension) to use for the stored Parquet file.
        secure (bool, optional): Use HTTPS if True. Defaults to False.

    Returns:
        str: The full MinIO path (bucket/object) to the uploaded file.

    Raises:
        ValueError: If the dataset is empty or required AWS credentials are missing.
        Exception: If upload to MinIO fails.
    """
    if not dataset:
        raise ValueError("extraction_results is empty")

    if isinstance(dataset, list):
        dataset = Dataset.from_list(dataset)
    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not access_key or not secret_key:
        raise ValueError("AWS credentials not found in environment variables.")

    # Create a temporary directory to store the Parquet file
    with tempfile.TemporaryDirectory() as temp_dir:
        parquet_filename = f"{filename}.parquet"
        parquet_path = os.path.join(temp_dir, parquet_filename)

        # Save to Parquet
        dataset.to_parquet(parquet_path)

        # Initialize MinIO client
        minio_client = Minio(
            minio_endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

        # Ensure the bucket exists
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)

        # Upload the file
        object_name = f"ocr_results/{parquet_filename}"
        try:
            minio_client.fput_object(
                bucket_name=bucket_name,
                object_name=object_name,
                file_path=parquet_path,
                content_type="application/octet-stream",
            )
        except Exception:
            print("Failed to upload file to MinIO")
            raise
        print(f"Uploaded {parquet_filename} to MinIO bucket {bucket_name}")
