import re
from dataclasses import asdict
from pathlib import Path

import torch
from datasets import Dataset
from PIL import Image
from vllm import LLM, EngineArgs, SamplingParams
from zenml import step

from pbd.helper.logger import setup_logger
from pbd.pipelines.ocr_engine.steps.downloader import (
    download_from_minio,
    extract_zip,
)
from pbd.pipelines.ocr_engine.steps.prompt import ocr_prompt
import time

logger = setup_logger(__name__)


def sort_pages_by_number(pages: list[str]) -> list[str]:
    def extract_number(filename: str) -> int:
        match = re.search(r"page_(\d+)", filename)
        return int(match.group(1)) if match else -1

    return sorted(pages, key=extract_number)


def extract_page_number(filename: str) -> int:
    """Extracts the numeric page number from a filename like 'page_23.jpg'."""
    match = re.search(r"page_(\d+)", Path(filename).stem)
    if match:
        return int(match.group(1))
    raise ValueError(f"Invalid filename format for page number: {filename}")


def do_inference(
    image_paths: list[str], model_path: str, max_new_tokens: int, batch_size: int
) -> list[dict]:
    engine_args = EngineArgs(
        model=model_path,
        max_num_seqs=1,
        limit_mm_per_prompt={"image": 5, "video": 0},
        mm_processor_kwargs={"min_pixels": 28 * 28, "max_pixels": 1280 * 80 * 80},
    )
    sampling_params = SamplingParams(
        max_tokens=max_new_tokens,
    )
    model = LLM(**asdict(engine_args))
    generated_texts = []
    total_batches = len(image_paths) // batch_size
    start = time.time()
    for indx in range(0, len(image_paths), batch_size):
        batch = image_paths[indx : indx + batch_size]
        inputs = [
            {
                "prompt": ocr_prompt,
                "multi_modal_data": {
                    "image": Image.open(img_path).convert("RGB"),
                },
            }
            for img_path in batch
        ]
        outputs = model.generate(inputs, sampling_params=sampling_params)
        logger.info(f"Processed batch {indx // batch_size}/{total_batches}")
        for img_path, output in zip(batch, outputs):
            page_no = extract_page_number(img_path)
            generated_texts.append(
                {
                    "page": page_no,
                    "content": output.outputs[0].text,
                }
            )
    logger.info(
        f"Generated texts: {len(generated_texts)} in {time.time() - start:.2f} seconds"
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
    batch_size: int = 5,
) -> Dataset:
    zip_path = download_from_minio(
        endpoint=endpoint,
        bucket=bucket,
        object_key=object_key,
        local_path=local_path,
    )
    image_paths = extract_zip(zip_path=zip_path, extract_to=extract_to)
    image_paths = sort_pages_by_number(pages=image_paths)
    logger.info(f"Extracted {len(image_paths)} images from {zip_path}")
    # check if cuda is available
    logger.info(f"CUDA available: {torch.cuda.is_available()}")
    outputs = do_inference(
        image_paths=image_paths,
        model_path=model_path,
        max_new_tokens=max_new_tokens,
        batch_size=batch_size,
    )
    # Convert list[dict] → Hugging Face Dataset
    dataset = Dataset.from_list(outputs)
    return dataset
