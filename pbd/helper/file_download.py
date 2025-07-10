import os
from pathlib import Path
from minio import Minio


def download_from_minio(
    endpoint: str,
    bucket: str,
    object_key: str,
    local_path: str,
) -> str:
    """
    Downloads a file from MinIO object storage to a local path.

    Args:
        endpoint (str): MinIO server endpoint (e.g., "localhost:9000").
        bucket (str): Name of the MinIO bucket.
        object_key (str): Object key (path) in the bucket.
        local_path (str): Local file path to save the downloaded file.

    Returns:
        str: The local file path where the object was saved.

    Raises:
        ValueError: If AWS credentials are missing in environment variables.
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

    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    client.fget_object(bucket, object_key, str(local_path))

    return str(local_path)
