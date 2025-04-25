import os
import tempfile
from datasets import Dataset
import pandas as pd
from datetime import datetime
from minio import Minio


def store_extracted_texts_to_minio(
    extraction_results: list[dict],
    bucket_name: str,
    minio_endpoint: str,
    access_key: str,
    secret_key: str,
    secure=False,
):
    """
    Store OCR extraction results as Parquet files in MinIO using the MinIO client

    Args:
        extraction_results: List of dicts with keys 'image_path', 'extracted_text'
        bucket_name: MinIO bucket name
        minio_endpoint: MinIO server endpoint
        access_key: MinIO access key
        secret_key: MinIO secret key
        secure: Use HTTPS if True
    """
    # Prepare data with metadata
    data = []
    for result in extraction_results:
        data.append(
            {
                "image_path": result["image_path"],
                "image_filename": os.path.basename(result["image_path"]),
                "extracted_text": result["extracted_text"],
                "extraction_timestamp": datetime.now().isoformat(),
            }
        )

    # Create dataset from the data
    df = pd.DataFrame(data)
    dataset = Dataset.from_pandas(df)

    # Create a temporary directory to store the Parquet file
    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate a filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parquet_filename = f"physics_ocr_{timestamp}.parquet"
        parquet_path = os.path.join(temp_dir, parquet_filename)

        # Save dataset to Parquet file
        dataset.to_parquet(parquet_path)

        # Initialize MinIO client
        minio_client = Minio(
            minio_endpoint, access_key=access_key, secret_key=secret_key, secure=secure
        )

        # Check if bucket exists, create if it doesn't
        found = minio_client.bucket_exists(bucket_name)
        if not found:
            minio_client.make_bucket(bucket_name)

        # Upload Parquet file to MinIO
        object_name = f"ocr_results/{parquet_filename}"
        minio_client.fput_object(
            bucket_name,
            object_name,
            parquet_path,
            content_type="application/octet-stream",
        )
        os.remove(parquet_path)
        return f"{bucket_name}/{object_name}"
