from vllm import LLM, SamplingParams
import re
from pathlib import Path
import time
from pbd.pipelines.ocr_engine.steps.process_image import fetch_image
from pbd.pipelines.ocr_engine.steps.prompt import build_no_anchoring_yaml_prompt
from pbd.pipelines.ocr_engine.steps.format import FrontMatterParser, PageResponse
import json


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


def parse_output(output: str) -> PageResponse:
    base_response_data = json.loads(output)

    model_response_markdown = base_response_data["choices"][0]["message"]["content"]

    parser = FrontMatterParser(front_matter_class=PageResponse)
    front_matter, text = parser._extract_front_matter_and_text(model_response_markdown)
    page_response = parser._parse_front_matter(front_matter, text)
    return page_response


def simple_inference(
    model: LLM,
    image_paths: list[str],
    batch_size: int,
    sampling_params: SamplingParams,
) -> list[dict]:
    generated_texts = []
    total_batches = len(image_paths) // batch_size
    print(f"Total batches to process: {total_batches}")
    for indx in range(0, len(image_paths), batch_size):
        batch = image_paths[indx : indx + batch_size]
        inputs = [
            {
                "prompt": build_no_anchoring_yaml_prompt(),
                "multi_modal_data": {
                    "image": fetch_image(img_path),
                },
            }
            for img_path in batch
        ]
        start = time.time()
        outputs = model.generate(
            inputs, use_tqdm=False, sampling_params=sampling_params
        )
        processed_outputs = [parse_output(output.outputs[0].text) for output in outputs]
        print(
            f"Processed batch {indx // batch_size} in {time.time() - start:.2f} seconds"
        )
        for img_path, output in zip(batch, processed_outputs):
            page_no = extract_page_number(img_path)
            generated_texts.append(
                {
                    "page": page_no,
                    "content": output.natural_text or "",
                }
            )
    return generated_texts
