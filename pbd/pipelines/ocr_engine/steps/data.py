import os
import tempfile
from datetime import datetime

from datasets import Dataset
from minio import Minio
from pbd.helper.logger import setup_logger
from zenml import step

logger = setup_logger(__name__)


@step(name="store_extracted_texts_to_minio", enable_step_logs=True, enable_cache=False)
def store_extracted_texts_to_minio(
    dataset: Dataset,
    bucket_name: str,
    minio_endpoint: str,
    secure=False,
):
    """
    Store OCR extraction results as Parquet files in MinIO using the MinIO client

    Args:
        dataset: List of dicts with keys 'image_path', 'extracted_text'
        bucket_name: MinIO bucket name
        minio_endpoint: MinIO server endpoint (e.g., "localhost:9000")
        access_key: MinIO access key
        secret_key: MinIO secret key
        secure: Use HTTPS if True

    Returns:
        The full MinIO path (bucket/object) to the uploaded file
    """
    if not dataset:
        raise ValueError("extraction_results is empty")

    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not access_key or not secret_key:
        raise ValueError("AWS credentials not found in environment variables.")

    # Create a temporary directory to store the Parquet file
    with tempfile.TemporaryDirectory() as temp_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parquet_filename = f"physics_ocr_{timestamp}.parquet"
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
            logger.exception("Failed to upload file to MinIO")
            raise
        logger.info(f"Uploaded {parquet_filename} to MinIO bucket {bucket_name}")
