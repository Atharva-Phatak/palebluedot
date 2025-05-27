import os
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


def upload_image(minio_client: Minio, bucket: str, key: str, image_path: str):
    minio_client.fput_object(
        bucket_name=bucket,
        object_name=key,
        file_path=image_path,
        content_type="image/jpeg",
    )
