from zenml import pipeline
from pbd.pipelines.data_extraction.steps.ocr import ocr_images
from pbd.pipelines.data_extraction.settings import (
    docker_settings,
    k8s_operator_settings,
)


@pipeline(
    settings={
        "docker": docker_settings,
        "orchestrator": k8s_operator_settings,
    },
    name="ocr_pipeline",
)
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
    ocr_images(
        endpoint=endpoint,
        bucket=bucket,
        object_key=object_key,
        local_path=local_path,
        extract_to=extract_to,
        model_path=model_path,
        max_new_tokens=max_new_tokens,
        min_pixels=min_pixels,
        max_pixels=max_pixels,
    )


if __name__ == "__main__":
    ocr_pipeline(
        endpoint="fsml-minio.info",
        bucket="data-bucket",
        object_key="processed_data/pdfs/dc_mechanics.zip",
        local_path="/tmp/images.zip",
        extract_to="/tmp/images",
        model_path="/models/Qwen2.5-VL-7B-Instruct-unsloth-bnb-4bit",
        max_new_tokens=4096,
        min_pixels=512,
        max_pixels=512,
    )
