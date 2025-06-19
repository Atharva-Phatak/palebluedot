import os
import tempfile

import pandas as pd
from minio import Minio

from pbd.helper.logger import setup_logger

logger = setup_logger(__name__)


def read_parquet_if_exists(
    endpoint: str, bucket_name: str, object_path: str
) -> pd.DataFrame | None:
    """
    Check if a Parquet file exists in MinIO at the given path and read it if it does.

    Args:
        minio_client (Minio): Authenticated MinIO client.
        bucket_name (str): The name of the bucket.
        object_path (str): Path of the Parquet file in the bucket.

    Returns:
        pd.DataFrame or None: Returns DataFrame if file exists, else None.
    """
    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not access_key or not secret_key:
        raise ValueError("AWS credentials not found in environment variables.")
    client = Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=False,
    )
    try:
        # Check if object exists
        client.stat_object(bucket_name, object_path)

        # Download to temp file
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            client.fget_object(bucket_name, object_path, tmp_file.name)
            df = pd.read_parquet(tmp_file.name)
        return df.to_dict(orient="records")

    except Exception as err:
        print(f"S3 error occurred: {err}")
        return None
    finally:
        if "tmp_file" in locals() and os.path.exists(tmp_file.name):
            os.remove(tmp_file.name)
