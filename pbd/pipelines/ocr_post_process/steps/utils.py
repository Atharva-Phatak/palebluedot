from transformers import AutoTokenizer
from pbd.pipelines.ocr_post_process.steps.prompt import generate_post_processing_prompt


def get_token_len(prompt: str, tokenizer) -> int:
    return len(tokenizer(prompt)["input_ids"])


def estimate_chunk_size_maximizing_coverage(
    data: list[dict],
    tokenizer,
    model_max_len: int,
    buffer: int = 200,
    max_chunk_size: int = 20,
) -> tuple[int, int]:
    """
    Find the largest chunk size (number of pages to concatenate) that fits within model_max_len.
    We test all possible consecutive chunks of each size and find the max size where
    at least some chunks fit within the limit.

    Returns:
        tuple: (best_chunk_size, max_token_len_for_that_chunk_size)
    """
    contents = [ex["content"] for ex in data]
    total_samples = len(contents)

    print(f"\n📊 Finding max pages to concatenate (up to {max_chunk_size})")
    print(f"📝 Total pages: {total_samples}")
    print(f"🧠 Model max length: {model_max_len}, buffer: {buffer}")
    print(
        f"🎯 Target: Find max chunk size where chunks can fit within {model_max_len - buffer} tokens"
    )

    best_chunk_size = 1
    best_max_token_len = 0

    # Start from largest chunk size and work down
    for chunk_size in range(max_chunk_size, 0, -1):
        max_token_len_this_size = 0
        fitting_chunks = 0
        total_chunks = 0

        # Test all possible consecutive chunks of this size
        for i in range(0, total_samples, chunk_size):
            chunk = contents[i : i + chunk_size]
            if not chunk:
                continue

            total_chunks += 1
            concat_text = "\n\n".join(chunk)
            prompt_text = generate_post_processing_prompt(concat_text)
            prompt = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt_text}],
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )

            token_len = get_token_len(prompt, tokenizer)
            max_token_len_this_size = max(max_token_len_this_size, token_len)

            # Count how many chunks fit within the limit
            if token_len + buffer <= model_max_len:
                fitting_chunks += 1

        # If we can fit at least some chunks of this size, this is our answer
        if fitting_chunks > 0:
            pages_processed = fitting_chunks * chunk_size
            coverage_pct = (pages_processed / total_samples) * 100
            print(
                f"✅ Chunk size {chunk_size:2d} pages | "
                f"Max token len = {max_token_len_this_size} | "
                f"With buffer: {max_token_len_this_size + buffer} | "
                f"Fitting chunks: {fitting_chunks}/{total_chunks} | "
                f"Coverage: {pages_processed}/{total_samples} pages ({coverage_pct:.1f}%)"
            )
            best_chunk_size = chunk_size
            best_max_token_len = max_token_len_this_size + buffer
            break
        else:
            print(
                f"❌ Chunk size {chunk_size:2d} pages | "
                f"Max token len = {max_token_len_this_size} | "
                f"With buffer: {max_token_len_this_size + buffer} > {model_max_len} | "
                f"No chunks fit!"
            )

    final_pages_processed = fitting_chunks * best_chunk_size
    final_coverage_pct = (final_pages_processed / total_samples) * 100

    print(
        f"\n✅ Best chunk size: {best_chunk_size} pages "
        f"(max prompt length: {best_max_token_len})"
    )
    print(
        f"📊 Coverage estimate: Will process {final_pages_processed}/{total_samples} pages "
        f"({final_coverage_pct:.1f}%)"
    )

    return best_chunk_size, best_max_token_len


def find_max_model_len_and_chunk_size(
    data: list[dict], model_path: str
) -> tuple[int, int]:
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model_max_len = getattr(tokenizer, "model_max_length", 40960)

    return estimate_chunk_size_maximizing_coverage(
        data,
        tokenizer,
        model_max_len=model_max_len,
        buffer=200,
        max_chunk_size=20,
    )
