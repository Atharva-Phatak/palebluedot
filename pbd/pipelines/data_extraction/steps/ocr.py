from transformers import AutoModelForImageTextToText, AutoProcessor
import torch
from PIL import Image
from zenml import step


def load_model_and_processor(model_path, min_pixels: int, max_pixels: int):
    model = AutoModelForImageTextToText.from_pretrained(
        model_path, torch_dtype=torch.float16, device_map="auto"
    )
    processor = AutoProcessor.from_pretrained(
        model_path, min_pixels=min_pixels, max_pixels=max_pixels
    )
    return model, processor


def build_prompt(images: list[str]):
    # Create a list of image content items
    image_content = [{"type": "image", "image": image} for image in images]

    # Create the full content list by adding the text prompt
    full_content = image_content + [
        {
            "type": "text",
            "text": r"""You are an expert OCR system specialized in extracting physics content from textbooks and notes. Extract all visible content from this image with precise formatting and structure preservation.

EXTRACTION GUIDELINES:
1. Mathematical content:
   - Preserve all equations exactly as written, maintaining proper notation for fractions, integrals, summations, etc.
   - Use LaTeX-style formatting for complex equations (e.g., \frac{a}{b}, \int_{a}^{b}, \sum_{i=1}^{n})
   - Maintain superscripts, subscripts, and special symbols (vectors, Greek letters, etc.)

2. Textual content:
   - Maintain paragraph structure and indentation
   - Preserve problem numbering schemes exactly (e.g., 1.2, Problem 3, Exercise 4.5)
   - Include all footnotes, margin notes, and annotations
   - Keep text formatting (bold, italics, underlining) when clearly visible

3. Visual elements:
   - Describe all diagrams, graphs, and figures concisely with [DIAGRAM: brief description]
   - Include all labels, axes, and legends from diagrams
   - Note coordinate systems and reference frames when present

4. Page structure:
   - Maintain the reading flow (columns, sections, etc.)
   - Include headers, footers, and page numbers if visible
   - Preserve section titles and hierarchical structure

OUTPUT FORMAT:
- Use markdown formatting for structure
- For multi-column layouts, process each column separately
- Separate distinct problems or sections clearly
- Use LaTeX-style notation within triple backticks for equation blocks
- For inline equations, use single $ delimiters

Transcribe everything you can see, maintaining the original organization and sequence of content.""",
        }
    ]

    # Return the complete message
    return [{"role": "user", "content": full_content}]


def process_template(images: list[Image], processor: AutoProcessor):
    prompt = build_prompt(images=images)
    text = processor.apply_chat_template(
        prompt, tokenize=False, add_generation_prompt=True
    )
    inputs = processor(
        text=[text],
        images=images,
        padding=True,
        return_tensors="pt",
    )
    return inputs


def do_inference(
    image,
    model: AutoModelForImageTextToText,
    processor: AutoProcessor,
    max_new_tokens: int,
):
    inputs = process_template(images=[image], processor=processor)
    with torch.no_grad():
        inputs = inputs.to("cuda")
        generated_ids = model.generate(**inputs, max_new_tokens=max_new_tokens)
    generated_ids_trimmed = [
        out_ids[len(in_ids) :]
        for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False,
    )
    return output_text[0]


@step
def ocr_images(
    image_paths: list[str],
    model_path: dict,
    max_new_tokens: int,
    min_pixels: int = 512,
    max_pixels: int = 512,
) -> list[str]:
    outputs = []
    model, processor = load_model_and_processor(
        model_path=model_path, min_pixels=min_pixels, max_pixels=max_pixels
    )
    for image_path in image_paths[300]:
        op = do_inference(
            image=image_path,
            model=model,
            processor=processor,
            max_new_tokens=max_new_tokens,
        )
        outputs.append(op)
    return outputs
