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
from pbd.pipelines.ocr_post_process.steps.prompt import generate_post_processing_prompt
from pbd.helper.s3_paths import formatted_results_path
from dataclasses import asdict
from pbd.helper.file_upload import store_extracted_texts_to_minio


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
    data: list[dict],
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
    tokenizer, model = load_model_and_tokenizer(
        max_model_len=max_model_len, model_path=model_path
    )
    params = vllm.SamplingParams(**sampling_params)

    results = []
    total_batches = len(data) // batch_size
    start = time.time()
    print(
        f"Starting inference with {len(data)} examples in batches of {batch_size}. Total batches: {total_batches}"
    )
    for indx in range(0, len(data), batch_size):
        batch = data[indx : indx + batch_size]
        contents = [ex["content"] for ex in batch]
        concat_contents = "\n\n".join(contents)
        # Pre-generate prompts in one go
        prompts = tokenizer.apply_chat_template(
            [
                {
                    "role": "user",
                    "content": generate_post_processing_prompt(concat_contents),
                }
            ],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )

        current_batch = indx // batch_size + 1
        print(
            f"Generated Prompts for batch : {current_batch}"
        )  # Track original content
        gen_time = time.time()
        outputs = model.generate(
            prompts=[prompts], use_tqdm=False, sampling_params=params
        )
        print(
            f"Batch : {current_batch} of {total_batches} | Time : {time.time() - gen_time:.2f} seconds"
        )
        results.append(
            {"content": concat_contents, "generated": outputs[0].outputs[0].text}
        )
    path = formatted_results_path(filename)
    print(
        f"Completed inference in {(time.time() - start)//60 :.2f} minutes. Storing results to MinIO at {path}"
    )
    store_extracted_texts_to_minio(
        dataset=results,
        bucket_name=bucket_name,
        minio_endpoint=minio_endpoint,
        filename=filename,
        path=path,
    )
    print(f"Results stored to MinIO at {path}")
