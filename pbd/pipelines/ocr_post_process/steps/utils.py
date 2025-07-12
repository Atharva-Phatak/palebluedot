from transformers import AutoTokenizer
from pbd.pipelines.ocr_post_process.steps.prompt import generate_post_processing_prompt


def get_token_len(prompt: str, tokenizer) -> int:
    return len(tokenizer(prompt)["input_ids"])


def find_max_model_len(data: list[dict], batch_size: int, model_path: str) -> int:
    """
    Calculate the average content length in the dataset.

    Args:
        data (list[dict]): List of dictionaries containing 'content' key.

    Returns:
        int: max model length based on the average content length in the dataset.
    """
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    token_lens = []
    for indx in range(0, len(data), batch_size):
        batch = data[indx : indx + batch_size]
        contents = [ex["content"] for ex in batch]
        concat_contents = "\n\n".join(contents)
        prompt = generate_post_processing_prompt(concat_contents)
        token_len = get_token_len(prompt=prompt, tokenizer=tokenizer)
        token_lens.append(token_len)
    avg_token_len = sum(token_lens) / len(token_lens)
    max_token_len = max(token_lens)
    token_len_to_use = max_token_len + 1000  # add some buffer
    pct95 = sorted(token_lens)[int(0.95 * len(token_lens))]
    print(
        f"Average content length in dataset: {avg_token_len} "
        f"Max content length: {max_token_len}"
        f"95th percentile: {pct95} for batch size {batch_size}"
    )
    print(f"Upper token limit: {max_token_len}")
    return token_len_to_use
