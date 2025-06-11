"""
Downloader and Extraction Utilities for OCR Engine

This module provides functions for downloading files from MinIO object storage and extracting images from zip archives.
These utilities are used in the OCR pipeline to retrieve and prepare image data for processing.

Functions:
    download_from_minio(endpoint, bucket, object_key, local_path):
        Downloads a file from MinIO to a local path.

    extract_zip(zip_path, extract_to):
        Extracts image files from a zip archive to a target directory.
"""

from minio import Minio
from pathlib import Path
from zipfile import ZipFile
import os


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


def extract_zip(zip_path: str, extract_to: str) -> list[str]:
    """
    Extracts image files from a zip archive to a target directory.

    Args:
        zip_path (str): Path to the zip archive.
        extract_to (str): Directory to extract files into.

    Returns:
        list[str]: List of extracted image file paths (jpg, jpeg, png).
    """
    zip_path = Path(zip_path)
    extract_to = Path(extract_to)
    extract_to.mkdir(parents=True, exist_ok=True)

    with ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)

    image_files = [
        str(p)
        for p in extract_to.glob("*")
        if p.suffix.lower() in [".jpg", ".jpeg", ".png"]
    ]
    return image_files
