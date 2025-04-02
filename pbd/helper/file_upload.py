import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from minio import Minio
from minio.error import S3Error
from pbd.helper.logger import setup_logger

logger = setup_logger(__name__)


def upload_single_file(client, file_path, bucket_name, object_name=None, prefix=""):
    """
    Upload a single file to MinIO

    Args:
        client: MinIO client instance
        file_path (str): Path to the file
        bucket_name (str): Name of the bucket
        object_name (str): Object name in MinIO (if None, uses filename)
        prefix (str): Optional prefix to add to object name
        logger (logging.Logger): Logger instance

    Returns:
        tuple: (success, file_path, error_message)
    """

    try:
        # If object_name is not given, use the file name
        if object_name is None:
            object_name = os.path.basename(file_path)

        if prefix:
            object_name = f"{prefix}/{object_name}"

        # Upload the file
        client.fput_object(
            bucket_name,
            object_name,
            file_path,
            content_type="audio/mp4",  # Correct MIME type for M4A files
        )
        logger.debug(f"Successfully uploaded: {file_path} as {object_name}")
        return (True, file_path, None)
    except S3Error as err:
        logger.error(f"S3Error uploading {file_path}: {err}")
        return (False, file_path, str(err))
    except Exception as err:
        logger.error(f"Unexpected error uploading {file_path}: {err}")
        return (False, file_path, str(err))


def batch_upload_m4a_to_minio(
    directory_path,
    bucket_name,
    endpoint=None,
    access_key=None,
    secret_key=None,
    secure=None,
    max_workers=10,
    recursive=False,
    prefix="",
    file_extension=".m4a",
):
    """
    Upload multiple M4A files to a MinIO bucket.

    Args:
        directory_path (str): Path to directory containing M4A files
        bucket_name (str): Name of the MinIO bucket
        endpoint (str): MinIO server endpoint (or None to use env var)
        access_key (str): MinIO access key (or None to use env var)
        secret_key (str): MinIO secret key (or None to use env var)
        secure (bool): Use HTTPS instead of HTTP (or None to use env var)
        max_workers (int): Maximum number of concurrent uploads
        recursive (bool): Recursively scan subdirectories
        prefix (str): Optional prefix to add to object names
        file_extension (str): File extension to filter for
        log_level (int): Logging level

    Returns:
        tuple: (success_count, error_count, errors)
    """

    # Get configuration from environment variables if not provided
    endpoint = endpoint or os.environ.get("MINIO_ENDPOINT", "localhost:9000")
    access_key = access_key or os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = secret_key or os.environ.get("MINIO_SECRET_KEY", "minioadmin")

    # Convert secure to bool if it's provided as a string in env var
    if secure is None:
        secure_env = os.environ.get("MINIO_SECURE", "False")
        secure = secure_env.lower() in ("true", "1", "yes")

    # Initialize MinIO client
    client = Minio(
        endpoint, access_key=access_key, secret_key=secret_key, secure=secure
    )

    logger.info(f"Connecting to MinIO at {endpoint} (secure={secure})")

    # Check if bucket exists and create if it doesn't
    if not client.bucket_exists(bucket_name):
        logger.info(f"Bucket '{bucket_name}' does not exist. Creating it now...")
        client.make_bucket(bucket_name)
        logger.info(f"Bucket '{bucket_name}' created successfully.")

    # Get list of files
    files_to_upload = []
    dir_path = Path(directory_path)

    if recursive:
        # Get all files recursively
        for file_path in dir_path.glob(f"**/*{file_extension}"):
            if file_path.is_file():
                files_to_upload.append(str(file_path))
    else:
        # Get only files in the specified directory
        for file_path in dir_path.glob(f"*{file_extension}"):
            if file_path.is_file():
                files_to_upload.append(str(file_path))

    if not files_to_upload:
        logger.warning(f"No {file_extension} files found in the specified directory.")
        return (0, 0, [])

    logger.info(f"Found {len(files_to_upload)} {file_extension} files to upload.")

    # Upload files in parallel
    success_count = 0
    error_count = 0
    errors = []

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                upload_single_file,
                client,
                file_path,
                bucket_name,
                prefix=prefix,
                logger=logger,
            )
            for file_path in files_to_upload
        ]

        for i, future in enumerate(futures):
            success, file_path, error_message = future.result()
            if success:
                success_count += 1
                logger.info(
                    f"[{i + 1}/{len(files_to_upload)}] Successfully uploaded: {os.path.basename(file_path)}"
                )
            else:
                error_count += 1
                errors.append((file_path, error_message))
                logger.error(
                    f"[{i + 1}/{len(files_to_upload)}] Failed to upload: {os.path.basename(file_path)} - {error_message}"
                )

    elapsed_time = time.time() - start_time
    logger.info("\nUpload summary:")
    logger.info(f"Total files: {len(files_to_upload)}")
    logger.info(f"Successfully uploaded: {success_count}")
    logger.info(f"Failed: {error_count}")
    logger.info(f"Total time: {elapsed_time:.2f} seconds")

    return (success_count, error_count, errors)
