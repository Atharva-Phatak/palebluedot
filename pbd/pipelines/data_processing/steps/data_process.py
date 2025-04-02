from pytubefix import YouTube
from pytubefix.cli import on_progress

from zenml import step
import os
from minio import Minio
from pbd.helper.logger import setup_logger
from pbd.helper.file_upload import upload_single_file

logger = setup_logger(__name__)


@step()
def download_youtube_audio(url: str, bucket_name: str, endpoint: str):
    # Get configuration from environment variables if not provided
    access_key = os.environ.get("AWS_ACCESS_KEY")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not access_key or not secret_key:
        raise ValueError("AWS credentials not found in environment variables.")

    # Initialize MinIO client
    client = Minio(
        endpoint=endpoint, access_key=access_key, secret_key=secret_key, secure=False
    )
    yt = YouTube(url, on_progress_callback=on_progress)
    logger.info(f"Downloading {yt.title}")
    ys = yt.streams.get_audio_only()
    path = ys.download(max_retries=1)
    if path is not None:
        logger.info(f"Downloaded {yt.title} to {path}")
        success, fpath, error_message = upload_single_file(
            client=client,
            file_path=path,
            bucket_name=bucket_name,
            prefix="yt_audio",
            object_name=yt.title,
        )
        if not success:
            logger.error(f"Error uploading {yt.title}: {error_message}")
