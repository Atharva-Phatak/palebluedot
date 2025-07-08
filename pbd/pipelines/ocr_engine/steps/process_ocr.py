from vllm import LLM, SamplingParams
from PIL import Image
import re
from pathlib import Path


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
    prompt: str,
    batch_size: int,
    sampling_params: SamplingParams,
) -> list[dict]:
    generated_texts = []
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
        print(f"Processed batch {indx // batch_size}")
        for img_path, output in zip(batch, outputs):
            page_no = extract_page_number(img_path)
            generated_texts.append(
                {
                    "page": page_no,
                    "content": output.outputs[0].text,
                }
            )
    return generated_texts
