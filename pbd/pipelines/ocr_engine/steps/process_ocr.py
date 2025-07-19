from vllm import LLM, SamplingParams
import re
from pathlib import Path
import time
from pbd.pipelines.ocr_engine.steps.process_image import fetch_image


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


def simple_inference(
    model: LLM,
    image_paths: list[str],
    prompts: dict[int, str],
    batch_size: int,
    sampling_params: SamplingParams,
) -> list[dict]:
    generated_texts = []
    total_batches = len(image_paths) // batch_size
    print(f"Total batches to process: {total_batches}")
    for indx in range(0, len(image_paths), batch_size):
        batch = image_paths[indx : indx + batch_size]
        pages = [extract_page_number(img_path) for img_path in batch]
        inputs = [
            {
                "prompt": prompts[page_no],
                "multi_modal_data": {
                    "image": fetch_image(img_path),
                },
            }
            for page_no,img_path in enumerate(pages,batch)
        ]
        start = time.time()
        outputs = model.generate(
            inputs, use_tqdm=False, sampling_params=sampling_params
        )
        print(
            f"Processed batch {indx // batch_size} in {time.time() - start:.2f} seconds"
        )
        for img_path, output in zip(batch, outputs):
            page_no = extract_page_number(img_path)
            generated_texts.append(
                {
                    "page": page_no,
                    "content": output.outputs[0].text,
                }
            )
    return generated_texts
