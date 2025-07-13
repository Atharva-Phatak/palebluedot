from transformers import AutoTokenizer
from pbd.pipelines.ocr_post_process.steps.prompt import generate_post_processing_prompt


def get_token_len(prompt: str, tokenizer) -> int:
    return len(tokenizer(prompt)["input_ids"])


def estimate_optimal_chunk_size(
    data: list[dict],
    tokenizer,
    model_max_len: int,
    buffer: int = 1000,
    max_batch_size: int = 20,
) -> tuple[int, int]:
    """
    Finds the largest batch size such that the concatenated prompt length stays within model_max_len.

    Returns:
        tuple: (optimal_batch_size, token_len_to_use)
    """
    n = len(data)
    best_batch_size = 1
    best_token_len = 0

    for batch_size in range(1, min(max_batch_size, n) + 1):
        token_lens = []

        for indx in range(0, n, batch_size):
            batch = data[indx : indx + batch_size]
            contents = [ex["content"] for ex in batch]
            concat_contents = "\n\n".join(contents)
            prompt = generate_post_processing_prompt(concat_contents)
            token_len = get_token_len(prompt=prompt, tokenizer=tokenizer)
            token_lens.append(token_len)

        max_token_len = max(token_lens)
        token_len_to_use = max_token_len + buffer

        if token_len_to_use <= model_max_len:
            best_batch_size = batch_size
            best_token_len = token_len_to_use
        else:
            break  # Further increasing batch_size will exceed model limit

    print(
        f"✅ Optimal batch size: {best_batch_size}, "
        f"Token len to use (with buffer): {best_token_len}, "
        f"Model max len: {model_max_len}"
    )

    return best_batch_size, best_token_len


def find_max_model_len_and_chunk_size(
    data: list[dict], model_path: str
) -> tuple[int, int]:
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model_max_len = getattr(tokenizer, "model_max_length", 40960)  # fallback default
    return estimate_optimal_chunk_size(data, tokenizer, model_max_len)
