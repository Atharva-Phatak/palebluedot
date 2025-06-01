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
    min_pixels: int = 512,
    max_pixels: int = 512,
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
        min_pixels=min_pixels,
        max_pixels=max_pixels,
    )
    store_extracted_texts_to_minio(
        extraction_results=data,
        bucket_name=bucket,
        minio_endpoint=endpoint,
    )


if __name__ == "__main__":
    config = load_config(config="configs/config.yaml")
    ocr_pipeline(
        endpoint=config.parameters.endpoint,
        bucket=config.parameters.bucket,
        object_key=config.parameters.object_key,
        local_path=config.parameters.local_path,
        extract_to=config.parameters.extract_to,
        model_path=config.parameters.model_path,
        max_new_tokens=4096,
        min_pixels=512,
        max_pixels=512,
    )
