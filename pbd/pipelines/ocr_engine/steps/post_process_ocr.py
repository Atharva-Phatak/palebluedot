from vllm import LLM, SamplingParams
from PIL import Image
import json
import copy
from pbd.helper.interface.pydantic_models import PageResponse
from pbd.pipelines.ocr_engine.steps.table_formatter import table_matrix2html
from pbd.pipelines.ocr_engine.steps.prompt import (
    build_element_merge_detect_prompt,
    build_qwen2_5_vl_prompt,
    build_html_table_merge_prompt,
)


def build_element_merge_detect_query(text_list_1, text_list_2) -> dict:
    image = Image.new("RGB", (28, 28), color="black")
    question = build_element_merge_detect_prompt(text_list_1, text_list_2)
    prompt = build_qwen2_5_vl_prompt(question)
    query = {
        "prompt": prompt,
        "multi_modal_data": {"image": image},
    }
    return query


def build_html_table_merge_query(text_1, text_2) -> dict:
    image = Image.new("RGB", (28, 28), color="black")
    question = build_html_table_merge_prompt(text_1, text_2)
    prompt = build_qwen2_5_vl_prompt(question)
    query = {
        "prompt": prompt,
        "multi_modal_data": {"image": image},
    }
    return query


def bulid_document_text(
    page_to_markdown_result, element_merge_detect_result, html_table_merge_result
):
    page_to_markdown_keys = list(page_to_markdown_result.keys())
    element_merge_detect_keys = list(element_merge_detect_result.keys())
    html_table_merge_keys = list(html_table_merge_result.keys())

    for page_1, page_2, elem_idx_1, elem_idx_2 in sorted(
        html_table_merge_keys, key=lambda x: -x[0]
    ):
        page_to_markdown_result[page_1][elem_idx_1] = html_table_merge_result[
            (page_1, page_2, elem_idx_1, elem_idx_2)
        ]
        page_to_markdown_result[page_2][elem_idx_2] = ""

    for page_1, page_2 in sorted(element_merge_detect_keys, key=lambda x: -x[0]):
        for elem_idx_1, elem_idx_2 in element_merge_detect_result[(page_1, page_2)]:
            if (
                len(page_to_markdown_result[page_1][elem_idx_1]) == 0
                or page_to_markdown_result[page_1][elem_idx_1][-1] == "-"
                or (
                    "\u4e00"
                    <= page_to_markdown_result[page_1][elem_idx_1][-1]
                    <= "\u9fff"
                )
            ):
                page_to_markdown_result[page_1][elem_idx_1] = (
                    page_to_markdown_result[page_1][elem_idx_1]
                    + ""
                    + page_to_markdown_result[page_2][elem_idx_2]
                )
            else:
                page_to_markdown_result[page_1][elem_idx_1] = (
                    page_to_markdown_result[page_1][elem_idx_1]
                    + " "
                    + page_to_markdown_result[page_2][elem_idx_2]
                )
            page_to_markdown_result[page_2][elem_idx_2] = ""

    document_text_list = []
    for page in page_to_markdown_keys:
        page_text_list = [s for s in page_to_markdown_result[page] if s]
        document_text_list += page_text_list
    return "\n\n".join(document_text_list)


def simple_inference(
    model: LLM,
    image_paths: list[str],
    prompt: str,
    batch_size: int,
    sampling_params: SamplingParams,
):
    base_outputs = []
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
        outputs = [output.outputs[0].text for output in outputs]
        base_outputs.extend(outputs)
    return base_outputs


def process_responses(
    model: LLM,
    image_paths: list[str],
    prompt: str,
    batch_size: int,
    max_new_tokens: int,
    max_page_retries: int = 3,
    skip_cross_page_merge: bool = False,
):
    num_pages = len(image_paths)
    print(f"Processing {num_pages} pages with batch size {batch_size}...")
    base_sampling_params = SamplingParams(temperature=0.0, max_tokens=max_new_tokens)
    retry_list = []
    page_to_markdown_result = {}
    base_outputs = simple_inference(
        model=model,
        image_paths=image_paths,
        prompt=prompt,
        batch_size=batch_size,
        sampling_params=base_sampling_params,
    )
    # Stage 1 : Process base outputs to markdown
    for indx, result in enumerate(base_outputs):
        try:
            json_data = json.loads(result)
            page_response = PageResponse(**json_data)
            natural_text = page_response.natural_text
            markdown_element_list = []
            for text in natural_text.split("\n\n"):
                if text.startswith("<Image>") and text.endswith("</Image>"):
                    pass
                elif text.startswith("<table>") and text.endswith("</table>"):
                    try:
                        new_text = table_matrix2html(text)
                    except Exception:
                        new_text = (
                            text.replace("<t>", "")
                            .replace("<l>", "")
                            .replace("<lt>", "")
                        )
                    markdown_element_list.append(new_text)
                else:
                    markdown_element_list.append(text)
            page_to_markdown_result[indx + 1] = markdown_element_list
        except Exception:
            retry_list.append(indx)

    retry_attempt = 0
    while len(retry_list) and retry_attempt < max_page_retries:
        retry_sampling_params = SamplingParams(
            temperature=0.1 * retry_attempt,
            max_tokens=max_new_tokens,
        )
        retry_paths = [image_paths[indx] for indx in retry_list]
        retry_outputs = simple_inference(
            model=model,
            image_paths=retry_paths,
            prompt=prompt,
            batch_size=batch_size,
            sampling_params=retry_sampling_params,
        )
        stage_2_retry_list = []
        for indx, result in zip(retry_list, retry_outputs):
            try:
                json_data = json.loads(result)
                page_response = PageResponse(**json_data)
                natural_text = page_response.natural_text
                markdown_element_list = []
                for text in natural_text.split("\n\n"):
                    if text.startswith("<Image>") and text.endswith("</Image>"):
                        pass
                    elif text.startswith("<table>") and text.endswith("</table>"):
                        try:
                            new_text = table_matrix2html(text)
                        except Exception:
                            new_text = (
                                text.replace("<t>", "")
                                .replace("<l>", "")
                                .replace("<lt>", "")
                            )
                        markdown_element_list.append(new_text)
                    else:
                        markdown_element_list.append(text)
                page_to_markdown_result[indx + 1] = markdown_element_list
            except Exception:
                stage_2_retry_list.append(indx)
        retry_list = stage_2_retry_list
        retry_attempt += 1

    page_texts = {}
    fallback_pages = []
    for page_number in range(1, num_pages + 1):
        if page_number not in page_to_markdown_result.keys():
            fallback_pages.append(page_number - 1)
        else:
            page_texts[str(page_number - 1)] = "\n\n".join(
                page_to_markdown_result[page_number]
            )

    if not skip_cross_page_merge:
        # Stage 2: Element Merge Detect
        print("Starting element merge detection...")
        element_merge_detect_keys = []
        element_merge_detect_query_list = []
        for page_num in range(1, num_pages):
            if (
                page_num in page_to_markdown_result.keys()
                and page_num + 1 in page_to_markdown_result.keys()
            ):
                element_merge_detect_query_list.append(
                    build_element_merge_detect_query(
                        page_to_markdown_result[page_num],
                        page_to_markdown_result[page_num + 1],
                    )
                )
                element_merge_detect_keys.append((page_num, page_num + 1))
        responses = model.generate(
            element_merge_detect_query_list, sampling_params=base_sampling_params
        )
        results = [response.outputs[0].text for response in responses]
        element_merge_detect_result = {}
        for key, result in zip(element_merge_detect_keys, results):
            try:
                element_merge_detect_result[key] = eval(result)
            except Exception:
                pass

        # Stage 3: HTML Table Merge
        print("Starting HTML table merge...")
        html_table_merge_keys = []
        for key, result in element_merge_detect_result.items():
            page_1, page_2 = key
            for elem_idx_1, elem_idx_2 in result:
                text_1 = page_to_markdown_result[page_1][elem_idx_1]
                text_2 = page_to_markdown_result[page_2][elem_idx_2]
                if (
                    text_1.startswith("<table>")
                    and text_1.endswith("</table>")
                    and text_2.startswith("<table>")
                    and text_2.endswith("</table>")
                ):
                    html_table_merge_keys.append(
                        (page_1, page_2, elem_idx_1, elem_idx_2)
                    )

        html_table_merge_keys = sorted(html_table_merge_keys, key=lambda x: -x[0])

        html_table_merge_result = {}
        page_to_markdown_result_tmp = copy.deepcopy(page_to_markdown_result)
        i = 0
        while i < len(html_table_merge_keys):
            tmp = set()
            keys = []
            while i < len(html_table_merge_keys):
                page_1, page_2, elem_idx_1, elem_idx_2 = html_table_merge_keys[i]
                if (page_2, elem_idx_2) in tmp:
                    break
                tmp.add((page_1, elem_idx_1))
                keys.append((page_1, page_2, elem_idx_1, elem_idx_2))
                i += 1

            html_table_merge_query_list = [
                build_html_table_merge_query(
                    page_to_markdown_result_tmp[page_1][elem_idx_1],
                    page_to_markdown_result_tmp[page_2][elem_idx_2],
                )
                for page_1, page_2, elem_idx_1, elem_idx_2 in keys
            ]
            responses = model.generate(
                html_table_merge_query_list, sampling_params=base_sampling_params
            )
            results = [response.outputs[0].text for response in responses]
            for key, result in zip(keys, results):
                if result.startswith("<table>") and result.endswith("</table>"):
                    html_table_merge_result[key] = result
                    page_to_markdown_result_tmp[page_1][elem_idx_1] = result

        document_text = bulid_document_text(
            page_to_markdown_result,
            element_merge_detect_result,
            html_table_merge_result,
        )
        return {
            "num_pages": num_pages,
            "document_text": document_text,
            "page_texts": page_texts,
            "fallback_pages": fallback_pages,
        }

    if skip_cross_page_merge:
        document_text_list = []
        for i in range(num_pages):
            if i not in fallback_pages:
                document_text_list.append(page_texts[str(i)])
        document_text = "\n\n".join(document_text_list)
        return {
            "num_pages": num_pages,
            "document_text": document_text,
            "page_texts": page_texts,
            "fallback_pages": fallback_pages,
        }
