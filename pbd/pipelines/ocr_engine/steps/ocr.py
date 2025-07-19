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

import torch
import vllm

from pbd.helper.file_upload import read_parquet_if_exists
from pbd.pipelines.ocr_engine.steps.downloader import (
    extract_zip,
)
from pbd.helper.file_download import download_from_minio
from pbd.helper.file_upload import store_extracted_texts_to_minio
from pbd.pipelines.ocr_engine.steps.process_ocr import simple_inference
from pbd.helper.s3_paths import ocr_results_path, pdf_prompt_path
from pbd.pipelines.ocr_engine.steps.format import clean_and_format_html


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


def process_response(response: list[dict]) -> list[dict]:
    cleaned_response = []
    for item in response:
        cleaned_response.append(
            {
                "page": item["page"],
                "content": clean_and_format_html(item["content"]),
            }
        )
    return cleaned_response


def do_inference(
    image_paths: list[str],
    model_path: str,
    max_new_tokens: int,
    batch_size: int,
    prompts: dict[int, str],
    max_model_len: int = 32768,
) -> list[dict]:
    """
    Runs OCR inference on a list of images using a multimodal LLM, batching requests for efficiency.

    Args:
        image_paths (list[str]): List of image file paths to process.
        model_path (str): Path to the pretrained multimodal LLM model.
        max_new_tokens (int): Maximum number of tokens to generate per output.
        batch_size (int): Number of images to process per batch.
        max_model_len (int, optional): Maximum model length for the LLM. Defaults to 32769.

    Returns:
        list[dict]: List of dictionaries with 'page' and 'content' keys for each image.
    """
    if torch.cuda.is_available():
        print("CUDA is available. Emptying cache")
        torch.cuda.empty_cache()
    print(f"Using vllm version {vllm.__version__}")
    engine_args = vllm.EngineArgs(
        model=model_path,
        max_num_seqs=batch_size,
        max_model_len=max_model_len,
        limit_mm_per_prompt={"image": batch_size, "video": 0},
        mm_processor_kwargs={"min_pixels": 28 * 28, "max_pixels": 1280 * 80 * 80},
    )
    model = vllm.LLM(**asdict(engine_args))
    sampling_params = vllm.SamplingParams(max_tokens=max_new_tokens)
    start = time.time()
    response = simple_inference(
        model=model,
        image_paths=image_paths,
        prompts=prompts,
        batch_size=batch_size,
        sampling_params=sampling_params,
    )

    total_time = (time.time() - start) // 60
    print(f"Total inference time: {total_time} minutes for {len(image_paths)} images")
    cleaned_response = process_response(response)
    print(f"Processed {len(cleaned_response)} images with OCR")
    return cleaned_response


def ocr_images(
    endpoint: str,
    bucket: str,
    minio_zip_path: str,
    local_path: str,
    model_path: str,
    extract_to: str,
    max_new_tokens: int,
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
        minio_zip_path (str): Object key for the zip file in MinIO.
        local_path (str): Local path to save the downloaded zip file.
        model_path (str): Path to the pretrained multimodal LLM model.
        extract_to (str): Directory to extract images to.
        max_new_tokens (int): Maximum number of tokens to generate per output.
        batch_size (int, optional): Number of images to process per batch. Defaults to 5.
        run_test (bool): If True, runs a test with a smaller batch of images.
        filename (str): Name of the file to store OCR results in MinIO.

    Returns:
        Dataset: Hugging Face Dataset containing OCR results for each image.
    """
    ocr_path = ocr_results_path(filename=filename)
    data = read_parquet_if_exists(
        endpoint=endpoint,
        bucket_name=bucket,
        object_path=ocr_path,
    )
    if data:
        print("Data already exists in MinIO. Returning existing data.")
        return data
    else:
        zip_path = download_from_minio(
            endpoint=endpoint,
            bucket=bucket,
            object_key=minio_zip_path,
            local_path=local_path,
        )
        image_paths = extract_zip(zip_path=zip_path, extract_to=extract_to)
        image_paths = sort_pages_by_number(pages=image_paths)
        if run_test:
            print(f"Running OCR inference test with {batch_size * 2} images")
            image_paths = image_paths[: batch_size * 2]
        print(f"Extracted {len(image_paths)} images from {zip_path}")
        # check if cuda is available
        print(f"CUDA available: {torch.cuda.is_available()}")
        prompt_path = pdf_prompt_path(filename=filename)
        prompts = download_from_minio(
            endpoint=endpoint,
            bucket=bucket,
            object_key=prompt_path,
            local_path="/tmp/prompts.json",
        )
        outputs = do_inference(
            image_paths=image_paths,
            model_path=model_path,
            max_new_tokens=max_new_tokens,
            batch_size=batch_size,
            prompts=prompts,
        )
        store_extracted_texts_to_minio(
            dataset=outputs,
            bucket_name=bucket,
            minio_endpoint=endpoint,
            filename=filename,
            path=ocr_path,
        )
        return outputs
