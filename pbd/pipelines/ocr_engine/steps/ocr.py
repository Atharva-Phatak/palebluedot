"""
OCR Engine Steps

This module provides functions and a ZenML step for performing OCR on images using a multimodal LLM.
It includes utilities for sorting image filenames, extracting page numbers, running inference in batches,
and converting results into a Hugging Face Dataset.

Functions:
    sort_pages_by_number(pages: list[str]) -> list[str]:
        Sorts a list of image filenames by their embedded page numbers.

    extract_page_number(filename: str) -> int:
        Extracts the numeric page number from a filename (e.g., 'page_23.jpg').

    do_inference(
        image_paths: list[str],
        model_path: str,
        max_new_tokens: int,
        batch_size: int
    ) -> list[dict]:
        Runs OCR inference on a list of images using a multimodal LLM, batching requests for efficiency.

    ocr_images(
        endpoint: str,
        bucket: str,
        object_key: str,
        local_path: str,
        model_path: str,
        extract_to: str,
        max_new_tokens: int,
        batch_size: int = 5
    ) -> Dataset:
        ZenML step that downloads a zip of images, extracts them, runs OCR, and returns a Hugging Face Dataset.
"""

import re
import time
from dataclasses import asdict
from pathlib import Path

import torch
import vllm
from PIL import Image
from zenml import log_metadata, step

from pbd.helper.logger import setup_logger
from pbd.pipelines.ocr_engine.steps.downloader import (
    download_from_minio,
    extract_zip,
)
from pbd.pipelines.ocr_engine.steps.upload_data import store_extracted_texts_to_minio

logger = setup_logger(__name__)


def sort_pages_by_number(pages: list[str]) -> list[str]:
    """
    Sorts a list of image filenames by their embedded page numbers.

    Args:
        pages (list[str]): List of image file paths or names containing 'page_<number>'.

    Returns:
        list[str]: Sorted list of image file paths/names by page number.
    """

    def extract_number(filename: str) -> int:
        match = re.search(r"page_(\d+)", filename)
        return int(match.group(1)) if match else -1

    return sorted(pages, key=extract_number)


def extract_page_number(filename: str) -> int:
    """
    Extracts the numeric page number from a filename like 'page_23.jpg'.

    Args:
        filename (str): The filename or path containing the page number.

    Returns:
        int: The extracted page number.

    Raises:
        ValueError: If the filename does not match the expected format.
    """
    match = re.search(r"page_(\d+)", Path(filename).stem)
    if match:
        return int(match.group(1))
    raise ValueError(f"Invalid filename format for page number: {filename}")


def do_inference(
    image_paths: list[str],
    model_path: str,
    max_new_tokens: int,
    batch_size: int,
    prompt: str,
) -> list[dict]:
    """
    Runs OCR inference on a list of images using a multimodal LLM, batching requests for efficiency.

    Args:
        image_paths (list[str]): List of image file paths to process.
        model_path (str): Path to the pretrained multimodal LLM model.
        max_new_tokens (int): Maximum number of tokens to generate per output.
        batch_size (int): Number of images to process per batch.
        prompt (str): The prompt to use for the OCR model.

    Returns:
        list[dict]: List of dictionaries with 'page' and 'content' keys for each image.
    """
    if torch.cuda.is_available():
        logger.info("CUDA is available. Emptying cache")
        torch.cuda.empty_cache()
    logger.info(f"Using vllm version {vllm.__version__}")
    engine_args = vllm.EngineArgs(
        model=model_path,
        max_num_seqs=10,
        max_model_len=100000,
        limit_mm_per_prompt={"image": 10, "video": 0},
        mm_processor_kwargs={"min_pixels": 28 * 28, "max_pixels": 1280 * 80 * 80},
    )
    sampling_params = vllm.SamplingParams(max_tokens=max_new_tokens, seed=42)
    model = vllm.LLM(**asdict(engine_args))
    generated_texts = []
    total_batches = len(image_paths) // batch_size
    start = time.time()
    for indx in range(0, len(image_paths), batch_size):
        batch = image_paths[indx : indx + batch_size]
        inputs = [
            {
                "prompt": prompt,
                "multi_modal_data": {
                    "image": Image.open(img_path).convert("RGB"),
                },
            }
            for img_path in batch
        ]
        outputs = model.generate(
            inputs, use_tqdm=False, sampling_params=sampling_params
        )
        logger.info(f"Processed batch {indx // batch_size}/{total_batches}")
        for img_path, output in zip(batch, outputs):
            page_no = extract_page_number(img_path)
            generated_texts.append(
                {
                    "page": page_no,
                    "content": output.outputs[0].text,
                }
            )
    total_time = (time.time() - start) // 60
    logger.info(f"Generated texts: {len(generated_texts)} in {total_time:.2f} minutes")
    log_metadata(
        metadata={"total_pages": len(generated_texts), "total_time": total_time}
    )
    return generated_texts


@step(enable_step_logs=True, enable_cache=False)
def ocr_images(
    endpoint: str,
    bucket: str,
    object_key: str,
    local_path: str,
    model_path: str,
    extract_to: str,
    max_new_tokens: int,
    prompt: str,
    run_test: bool,
    filename: str,
    batch_size: int = 5,
) -> list:
    """
    ZenML step that downloads a zip of images from MinIO, extracts them, runs OCR inference,
    and returns the results as a list

    Args:
        endpoint (str): MinIO endpoint URL.
        bucket (str): MinIO bucket name.
        object_key (str): Object key for the zip file in MinIO.
        local_path (str): Local path to save the downloaded zip file.
        model_path (str): Path to the pretrained multimodal LLM model.
        extract_to (str): Directory to extract images to.
        max_new_tokens (int): Maximum number of tokens to generate per output.
        batch_size (int, optional): Number of images to process per batch. Defaults to 5.
        prompt (str): The prompt to use for the OCR model.

    Returns:
        Dataset: Hugging Face Dataset containing OCR results for each image.
    """
    zip_path = download_from_minio(
        endpoint=endpoint,
        bucket=bucket,
        object_key=object_key,
        local_path=local_path,
    )
    image_paths = extract_zip(zip_path=zip_path, extract_to=extract_to)
    image_paths = sort_pages_by_number(pages=image_paths)
    if run_test:
        logger.warning(f"Running OCR inference test with {batch_size * 2} images")
        image_paths = image_paths[: batch_size * 2]
    logger.info(f"Extracted {len(image_paths)} images from {zip_path}")
    # check if cuda is available
    logger.info(f"CUDA available: {torch.cuda.is_available()}")
    outputs = do_inference(
        image_paths=image_paths,
        model_path=model_path,
        max_new_tokens=max_new_tokens,
        batch_size=batch_size,
        prompt=prompt,
    )
    store_extracted_texts_to_minio(
        dataset=outputs,
        bucket_name=bucket,
        minio_endpoint=endpoint,
        filename=filename,
    )
    return outputs
