from omegaconf import OmegaConf
from zenml import pipeline

from pbd.pipelines.ocr_engine.settings import (
    docker_settings,
    k8s_operator_settings,
)
from pbd.pipelines.ocr_engine.steps.data import store_extracted_texts_to_minio
from pbd.pipelines.ocr_engine.steps.ocr import ocr_images


def load_config(config_path: str):
    return OmegaConf.load(config_path)


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
    filename: str,
):
    """Pipeline for performing OCR on images extracted from a zip file."""
    data = ocr_images(
        endpoint=endpoint,
        bucket=bucket,
        object_key=object_key,
        local_path=local_path,
        extract_to=extract_to,
        model_path=model_path,
        max_new_tokens=max_new_tokens,
    )
    store_extracted_texts_to_minio(
        dataset=data, bucket_name=bucket, minio_endpoint=endpoint, filename=filename
    )


if __name__ == "__main__":
    # config_dir = get_pipeline_config_dir(pipeline_name="ocr_engine")
    # config = load_config(config_path=str(config_dir / "config.yaml"))
    ocr_pipeline(
        endpoint="fsml-minio.info",
        bucket="data-bucket",
        object_key="processed_data/pdfs/dc_mechanics.zip",
        local_path="/tmp/images.zip",
        extract_to="/tmp/images",
        model_path="/models/Qwen2.5-VL-7B-Instruct-unsloth-bnb-4bit",
        max_new_tokens=10404,
        filename="dc_mechanics",
    )
