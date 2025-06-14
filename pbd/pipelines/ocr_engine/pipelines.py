from zenml import pipeline

from pbd.helper.logger import setup_logger
from pbd.pipelines.ocr_engine.settings import (
    docker_settings,
    k8s_operator_settings,
)
from pbd.pipelines.ocr_engine.steps.data import store_extracted_texts_to_minio
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
    )
    store_extracted_texts_to_minio(
        dataset=data,
        bucket_name=bucket,
        minio_endpoint=endpoint,
        filename=filename,
    )
    logger.info(
        f"OCR results stored in MinIO bucket '{bucket}' with filename '{filename}'."
    )
    dataset = extract_problem_solution(
        data=data,
        model_path=post_process_model_path,
        sampling_params=post_process_sampling_params,
        batch_size=post_process_batch_size,
    )
    store_extracted_texts_to_minio(
        dataset=dataset,
        bucket_name=bucket,
        minio_endpoint=endpoint,
        filename=f"{filename}_post_processed",
    )


if __name__ == "__main__":
    ocr_pipeline(
        endpoint="palebluedot-minio.io",
        bucket="data-bucket",
        object_key="processed_data/pdfs/dc_mechanics.zip",
        local_path="/tmp/images.zip",
        extract_to="/tmp/images",
        model_path="/models/Qwen2.5-VL-7B-Instruct-unsloth-bnb-4bit",
        max_new_tokens=32768,
        prompt=ocr_prompt,
        filename="dc_mechanics",
        post_process_model_path="/models/Qwen3-1.7B",
        post_process_sampling_params={
            "temperature": 0.6,
            "top_p": 0.8,
            "top_k": 20,
            "max_tokens": 32768,
        },
        post_process_batch_size=5,
        run_test=False,
    )
