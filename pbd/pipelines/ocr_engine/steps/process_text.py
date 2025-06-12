import time
from typing import List

import torch
from datasets import Dataset
from transformers import AutoTokenizer
from vllm import LLM, SamplingParams
from zenml import step

from pbd.helper.logger import setup_logger
from pbd.pipelines.ocr_engine.steps.prompt import generate_post_processing_prompt

logger = setup_logger(__name__)


def load_model_and_tokenizer(model_path: str):
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    vllm_model = LLM(model=model_path)
    return tokenizer, vllm_model


@step(enable_step_logs=True, enable_cache=False)
def extract_problem_solution(
    data: Dataset, model_path: str, sampling_params: dict, batch_size: int
) -> List[dict]:
    # empty cuda cache before starting new step
    if torch.cuda.is_available():
        logger.warning("Emptying cuda cache before starting new step.")
        torch.cuda.empty_cache()
    tokenizer, vllm_model = load_model_and_tokenizer(model_path)
    params = SamplingParams(**sampling_params)

    results = []
    start = time.time()

    for indx in range(0, len(data), batch_size):
        batch = data[indx : indx + batch_size]

        prompts = []
        contents = []
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
            contents.append(content)  # Track original content

        outputs = vllm_model.generate(prompts, params)

        for content, output in zip(contents, outputs):
            results.append({"content": content, "generated": output.outputs[0].text})

    logger.info(f"Completed inference in {time.time() - start:.2f} seconds.")
    results = Dataset.from_list(results)
    return results
