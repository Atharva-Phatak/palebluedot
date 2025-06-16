from zenml import pipeline

from pbd.helper.logger import setup_logger
from pbd.pipelines.ocr_engine.settings import (
    docker_settings,
    k8s_operator_settings,
)
from pbd.pipelines.ocr_engine.steps.ocr import ocr_images
from pbd.pipelines.ocr_engine.steps.process_text import extract_problem_solution
from pbd.pipelines.ocr_engine.steps.prompt import ocr_prompt

logger = setup_logger(__name__)


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
    prompt: str,
    filename: str,
    extraction_batch_size: int,
    post_process_model_path: str,
    post_process_sampling_params: dict,
    post_process_batch_size: int,
    run_test: bool = False,
):
    """Pipeline for performing OCR on images extracted from a zip file."""
    logger.info("Starting OCR pipeline")
    data = ocr_images(
        endpoint=endpoint,
        bucket=bucket,
        object_key=object_key,
        local_path=local_path,
        extract_to=extract_to,
        model_path=model_path,
        prompt=prompt,
        max_new_tokens=max_new_tokens,
        run_test=run_test,
        filename=filename,
        batch_size=extraction_batch_size,
    )
    logger.info(
        f"OCR results stored in MinIO bucket '{bucket}' with filename '{filename}'."
    )
    extract_problem_solution(
        data=data,
        model_path=post_process_model_path,
        sampling_params=post_process_sampling_params,
        batch_size=post_process_batch_size,
        bucket_name=bucket,
        filename=f"{filename}_post_processed",
        minio_endpoint=endpoint,
    )


if __name__ == "__main__":
    ocr_pipeline(
        endpoint="palebluedot-minio.io",
        bucket="data-bucket",
        object_key="processed_data/pdfs/dc_mechanics.zip",
        local_path="/tmp/images.zip",
        extract_to="/tmp/images",
        model_path="/models/Nanonets-OCR-s",
        max_new_tokens=80000,
        prompt=ocr_prompt,
        filename="dc_mechanics",
        extraction_batch_size=20,
        post_process_model_path="/models/Qwen3-4B-unsloth-bnb-4bit",
        post_process_sampling_params={
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 20,
            "max_tokens": 80000,
        },
        post_process_batch_size=20,
        run_test=True,
    )
