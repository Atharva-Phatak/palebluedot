from zenml import pipeline
from pbd.pipelines.data_extraction.steps.downloader import (
    download_from_minio,
    extract_zip,
)
from pbd.pipelines.data_extraction.steps.ocr import ocr_images
import os


@pipeline
def ocr_pipeline(
    endpoint: str,
    bucket: str,
    object_key: str,
    local_path: str,
    extract_to: str,
    model_path: str,
    max_new_tokens: int,
    min_pixels: int = 512,
    max_pixels: int = 512,
):
    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not access_key or not secret_key:
        raise ValueError("AWS credentials not found in environment variables.")
    zip_path = download_from_minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        bucket=bucket,
        object_key=object_key,
        local_path=local_path,
    )
    image_paths = extract_zip(zip_path=zip_path, extract_to=extract_to)
    ocr_images(
        image_paths=image_paths,
        model_path=model_path,
        max_new_tokens=max_new_tokens,
        min_pixels=min_pixels,
        max_pixels=max_pixels,
    )


if __name__ == "__main__":
    ocr_pipeline.with_options(
        config_path="pbd/pipelines/data_extraction/config/config.yaml"
    )()
