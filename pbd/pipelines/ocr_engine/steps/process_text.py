"""
This module provides functionality for extracting problem-solution pairs from a dataset using a large language model (LLM) with the vLLM inference engine. It includes utilities for loading models and tokenizers, generating prompts, and running batched inference with sampling parameters.

Main Components:
----------------
- `load_model_and_tokenizer`: Loads a HuggingFace tokenizer and a vLLM model from a specified path.
- `extract_problem_solution`: A ZenML step that processes a HuggingFace Dataset, generates prompts for each example, runs inference in batches, and returns the generated outputs alongside the original content.

Dependencies:
-------------
- torch
- datasets
- transformers
- vllm
- zenml
- pbd.helper.logger
- pbd.pipelines.ocr_engine.steps.prompt

Usage:
------
This module is intended to be used as part of a ZenML pipeline for post-processing OCR outputs or similar tasks where LLM-based extraction of structured information is required.

Logging:
--------
A logger is set up for monitoring and debugging purposes.

"""

import time

import torch
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams
from zenml import step

from pbd.helper.logger import setup_logger
from pbd.pipelines.ocr_engine.steps.prompt import generate_post_processing_prompt
from pbd.pipelines.ocr_engine.steps.upload_data import store_extracted_texts_to_minio

logger = setup_logger(__name__)


def load_model_and_tokenizer(model_path: str):
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    vllm_model = LLM(model=model_path, max_num_seqs=10)
    return tokenizer, vllm_model


@step(enable_step_logs=True, enable_cache=False)
def extract_problem_solution(
    data: list[dict],
    model_path: str,
    sampling_params: dict,
    batch_size: int,
    bucket_name: str,
    filename: str,
    minio_endpoint: str,
):
    # empty cuda cache before starting new step
    if torch.cuda.is_available():
        logger.warning("Emptying cuda cache before starting new step.")
        torch.cuda.empty_cache()
    tokenizer, vllm_model = load_model_and_tokenizer(model_path)
    params = SamplingParams(**sampling_params)

    results = []
    total_batches = len(data) // batch_size
    start = time.time()
    for indx in range(0, len(data), batch_size):
        batch = data[indx : indx + batch_size]
        prompts = []
        contents = []
        pages = []
        for example in batch:
            content = example["content"]
            prompt = generate_post_processing_prompt(content)
            messages = [{"role": "user", "content": prompt}]
            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )
            prompts.append(text)
            contents.append(content)
            pages.append(example["page"])  # Track original content
        gen_time = time.time()
        outputs = vllm_model.generate(
            prompts=prompts, use_tqdm=False, sampling_params=params
        )
        logger.info(
            f"Batch : {indx + 1} of {total_batches} | Time : {time.time() - gen_time:.2f} seconds"
        )
        for content, output, page in zip(contents, outputs, pages):
            results.append(
                {"content": content, "generated": output.outputs[0].text, "page": page}
            )

    logger.info(f"Completed inference in {time.time() - start:.2f} seconds.")
    store_extracted_texts_to_minio(
        dataset=results,
        bucket_name=bucket_name,
        minio_endpoint=minio_endpoint,
        filename=filename,
    )
