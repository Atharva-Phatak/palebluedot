from PIL import Image
from vllm import LLM, EngineArgs, SamplingParams
from pbd.pipelines.ocr_engine.steps.prompt import ocr_prompt
from zenml import step
from pbd.helper.logger import setup_logger
from pbd.pipelines.ocr_engine.steps.downloader import (
    download_from_minio,
    extract_zip,
)
import torch
from dataclasses import asdict
from datasets import Dataset

logger = setup_logger(__name__)


def do_inference(
    image_paths: list[str], model_path: str, max_new_tokens: int
) -> list[dict]:
    engine_args = EngineArgs(
        model=model_path,
        max_model_len=4096,
        max_num_seqs=1,
        limit_mm_per_prompt={"image": 2, "video": 0},
        mm_processor_kwargs={"min_pixels": 28 * 28, "max_pixels": 1280 * 80 * 80},
    )
    sampling_params = SamplingParams(
        max_tokens=max_new_tokens,
    )
    model = LLM(**asdict(engine_args))
    generated_texts = []
    for page_no, image in enumerate(image_paths):
        image = Image.open(image).convert("RGB")
        inputs = {
            "prompt": ocr_prompt,
            "multi_modal_data": {
                "image": image,
            },
        }
        outputs = model.generate([inputs], sampling_params=sampling_params)
        generated_texts.append({"page": page_no, "content": outputs[0].outputs[0].text})
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
) -> Dataset:
    zip_path = download_from_minio(
        endpoint=endpoint,
        bucket=bucket,
        object_key=object_key,
        local_path=local_path,
    )
    image_paths = extract_zip(zip_path=zip_path, extract_to=extract_to)
    logger.info(f"Extracted {len(image_paths)} images from {zip_path}")
    # check if cuda is available
    logger.info(f"CUDA available: {torch.cuda.is_available()}")
    outputs = do_inference(
        image_paths=image_paths,
        model_path=model_path,
        max_new_tokens=max_new_tokens,
    )
    # Convert list[dict] → Hugging Face Dataset
    dataset = Dataset.from_list(outputs)
    return dataset
