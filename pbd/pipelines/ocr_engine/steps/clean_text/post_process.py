# Adapted from : https://github.com/rednote-hilab/dots.ocr/tree/master/dots_ocr
from PIL import Image
from typing import List, Dict
from pbd.pipelines.ocr_engine.steps.process_image import (
    smart_resize,
    MIN_PIXELS,
    MAX_PIXELS,
)
import json

from pbd.pipelines.ocr_engine.steps.clean_text.markdown import layoutjson2md
from pbd.pipelines.ocr_engine.steps.clean_text.output_cleaner import OutputCleaner


def post_process_cells(
    origin_image: Image.Image,
    cells: List[Dict],
    input_width,  # server input width, also has smart_resize in server
    input_height,
    factor: int = 28,
    min_pixels: int = 3136,
    max_pixels: int = 11289600,
) -> List[Dict]:
    """
    Post-processes cell bounding boxes, converting coordinates from the resized dimensions back to the original dimensions.

    Args:
        origin_image: The original PIL Image.
        cells: A list of cells containing bounding box information.
        input_width: The width of the input image sent to the server.
        input_height: The height of the input image sent to the server.
        factor: Resizing factor.
        min_pixels: Minimum number of pixels.
        max_pixels: Maximum number of pixels.

    Returns:
        A list of post-processed cells.
    """
    assert isinstance(cells, list) and len(cells) > 0 and isinstance(cells[0], dict)
    min_pixels = min_pixels or MIN_PIXELS
    max_pixels = max_pixels or MAX_PIXELS
    original_width, original_height = origin_image.size

    input_height, input_width = smart_resize(
        input_height, input_width, min_pixels=min_pixels, max_pixels=max_pixels
    )

    scale_x = input_width / original_width
    scale_y = input_height / original_height

    cells_out = []
    for cell in cells:
        bbox = cell["bbox"]
        bbox_resized = [
            int(float(bbox[0]) / scale_x),
            int(float(bbox[1]) / scale_y),
            int(float(bbox[2]) / scale_x),
            int(float(bbox[3]) / scale_y),
        ]
        cell_copy = cell.copy()
        cell_copy["bbox"] = bbox_resized
        cells_out.append(cell_copy)

    return cells_out


def post_process_response(
    model_response,
    input_image: Image.Image,
    origin_image: Image.Image,
    min_pixels: int = MIN_PIXELS,
    max_pixels: int = MAX_PIXELS,
):
    json_load_failed = False
    cells = model_response
    try:
        cells = json.loads(cells)
        cells = post_process_cells(
            origin_image,
            cells,
            input_image.width,
            input_image.height,
            min_pixels=min_pixels,
            max_pixels=max_pixels,
        )
        return cells, False
    except Exception as e:
        print(f"cells post process error: {e}")
        json_load_failed = True

    if json_load_failed:
        cleaner = OutputCleaner()
        response_clean = cleaner.clean_model_output(cells)
        if isinstance(response_clean, list):
            response_clean = "\n\n".join(
                [cell["text"] for cell in response_clean if "text" in cell]
            )
        return response_clean, True


def post_process_output(
    model_response,
    input_image: Image.Image,
    origin_image: Image.Image,
    min_pixels: int = MIN_PIXELS,
    max_pixels: int = MAX_PIXELS,
):
    """
    Post-processes the model response to extract cells and clean the output.

    Args:
        model_response: The raw response from the OCR model.
        input_image: The input image sent to the server.
        origin_image: The original image before resizing.
        min_pixels: Minimum number of pixels for resizing.
        max_pixels: Maximum number of pixels for resizing.

    Returns:
        A tuple containing the processed cells or cleaned output, and a boolean indicating if cleaning was needed.
    """
    cells, filtering_needed = post_process_response(
        model_response=model_response,
        input_image=input_image,
        origin_image=origin_image,
        min_pixels=min_pixels,
        max_pixels=max_pixels,
    )
    if filtering_needed:
        return {
            "json_metadata": model_response,
            "markdown_content": cells,
            "json_load_failed": True,
        }
    else:
        markdown_content = layoutjson2md(
            image=origin_image,
            cells=cells,
            text_key="text",
        )
        return {
            "json_metadata": cells,
            "markdown_content": markdown_content,
            "json_load_failed": False,
        }
