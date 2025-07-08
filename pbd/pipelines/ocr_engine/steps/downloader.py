"""
================================================================================
Downloader and Extraction Utilities for OCR Engine
================================================================================

This module provides utility functions to facilitate the downloading of files from
MinIO object storage and the extraction of image files from zip archives. These
utilities are essential components in the OCR (Optical Character Recognition)
pipeline, enabling seamless retrieval and preparation of image data for further
processing.

--------------------------------------------------------------------------------
Overview
--------------------------------------------------------------------------------

The module includes the following core functionalities:

1. Downloading Files from MinIO:
   - Securely downloads files from a specified MinIO bucket using credentials
     provided via environment variables.
   - Ensures the target directory exists before saving the downloaded file.
   - Raises informative errors if credentials are missing.

2. Extracting Images from Zip Archives:
   - Extracts all files from a given zip archive into a specified directory.
   - Filters and returns only image files with extensions: .jpg, .jpeg, .png.
   - Automatically creates the extraction directory if it does not exist.

--------------------------------------------------------------------------------
Environment Variables
--------------------------------------------------------------------------------

The following environment variables must be set for MinIO access:

- AWS_ACCESS_KEY_ID:     The access key for MinIO.
- AWS_SECRET_ACCESS_KEY: The secret key for MinIO.

If these variables are not set, the download function will raise a ValueError.

--------------------------------------------------------------------------------
Functions
--------------------------------------------------------------------------------

download_from_minio(endpoint, bucket, object_key, local_path)
    Downloads a file from a MinIO bucket to a specified local path.
    - endpoint:    The MinIO server endpoint (e.g., "localhost:9000").
    - bucket:      The name of the MinIO bucket.
    - object_key:  The object key (path) within the bucket.
    - local_path:  The local filesystem path to save the downloaded file.
    Returns the path to the downloaded file as a string.

extract_zip(zip_path, extract_to)
    Extracts all files from a zip archive to a target directory, returning a list
    of extracted image file paths (with extensions .jpg, .jpeg, .png).
    - zip_path:    Path to the zip archive.
    - extract_to:  Directory to extract files into.
    Returns a list of strings representing the paths to the extracted image files.

--------------------------------------------------------------------------------
Usage Example
--------------------------------------------------------------------------------

    from ocr_utils import download_from_minio, extract_zip

    # Download a zip file from MinIO
    zip_file = download_from_minio(
        endpoint="localhost:9000",
        bucket="ocr-images",
        object_key="batch1/images.zip",
        local_path="/tmp/images.zip"
    )

    # Extract images from the downloaded zip file
    image_paths = extract_zip(
        zip_path=zip_file,
        extract_to="/tmp/images"
    )

    print("Extracted images:", image_paths)

--------------------------------------------------------------------------------
Dependencies
--------------------------------------------------------------------------------

- minio:      For interacting with MinIO object storage.
- pathlib:    For filesystem path manipulations.
- zipfile:    For handling zip archives.
- os:         For accessing environment variables.

--------------------------------------------------------------------------------
Exceptions
--------------------------------------------------------------------------------

- ValueError: Raised by download_from_minio if required environment variables
              for MinIO credentials are missing.

Downloader and Extraction Utilities for OCR Engine

This module provides functions for downloading files from MinIO object storage and extracting images from zip archives.
These utilities are used in the OCR pipeline to retrieve and prepare image data for processing.

Functions:
    download_from_minio(endpoint, bucket, object_key, local_path):
        Downloads a file from MinIO to a local path.

    extract_zip(zip_path, extract_to):
        Extracts image files from a zip archive to a target directory.
"""


import os
from pathlib import Path
from zipfile import ZipFile

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
