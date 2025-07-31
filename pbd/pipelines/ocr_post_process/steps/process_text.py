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
import vllm
from pbd.pipelines.ocr_post_process.steps.prompt import get_segmentation_prompt
from pbd.helper.s3_paths import formatted_results_path
from dataclasses import asdict
from pbd.helper.file_upload import store_extracted_texts_to_minio


def process_prompts(tokenizer, batch: list) -> list[tuple[str, list[dict]]]:
    prompts, contents = [], []
    for example in batch:
        prompt = get_segmentation_prompt(example)
        messages = [{"role": "user", "content": prompt}]
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        prompts.append(text)
        contents.append(example)
    return prompts, contents


def load_model_and_tokenizer(model_path: str, batch_size: int, max_model_len: int):
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    engine_args = vllm.EngineArgs(
        model=model_path,
        max_num_seqs=batch_size,
        max_model_len=max_model_len,
        enable_prefix_caching=True,
    )
    model = vllm.LLM(**asdict(engine_args))
    print(
        f"Loaded model from {model_path} with batch size 1 and max model length {max_model_len}"
    )
    return tokenizer, model


def extract_problem_solution(
    max_model_len: int,
    data: list,
    model_path: str,
    sampling_params: dict,
    bucket_name: str,
    batch_size: int,
    filename: str,
    minio_endpoint: str,
):
    # empty cuda cache before starting new step
    if torch.cuda.is_available():
        print("Emptying cuda cache before starting new step.")
        torch.cuda.empty_cache()
    results = []
    tokenizer, model = load_model_and_tokenizer(
        max_model_len=max_model_len, model_path=model_path, batch_size=batch_size
    )
    params = vllm.SamplingParams(**sampling_params)
    start = time.time()
    total_batches = len(data) // batch_size
    print(f"Total batches to process: {total_batches}")
    for indx in range(0, len(data), batch_size):
        batch_slice = data[indx : indx + batch_size]
        current_prompts, current_contents = process_prompts(tokenizer, batch_slice)
        gen_time = time.time()
        outputs = model.generate(
            prompts=current_prompts, sampling_params=params, use_tqdm=False
        )
        for chunk, output in zip(current_contents, outputs):
            generated_text = output.outputs[0].text
            results.append({"content": chunk, "generated": generated_text})
        print(f"Batch {indx} processed in {(time.time() - gen_time):.2f} seconds, ")
    path = formatted_results_path(filename)
    print(
        f"\n🎉 Completed inference in {(time.time() - start) // 60:.2f} minutes. Storing results to MinIO at {path}"
    )
    store_extracted_texts_to_minio(
        dataset=results,
        bucket_name=bucket_name,
        minio_endpoint=minio_endpoint,
        filename=filename,
        path=path,
    )
    print(f"Results stored to MinIO at {path}")
