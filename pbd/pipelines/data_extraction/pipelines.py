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
    model_config: dict,
    generation_config: dict,
    prompt: str,
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
        model_config=model_config,
        generation_config=generation_config,
        prompt=prompt,
    )


if __name__ == "__main__":
    ocr_pipeline.with_options(config_path="./config/config.yaml")()
