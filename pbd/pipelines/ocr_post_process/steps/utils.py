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
    target_coverage: float = 0.99,
) -> tuple[int, int]:
    """
    Find the chunk size that allows processing the max number of examples
    while keeping prompt length <= model_max_len.

    Returns:
        tuple: (best_chunk_size, token_len_to_use)
    """
    contents = [ex["content"] for ex in data]
    total_samples = len(contents)

    print(f"\n📊 Starting chunk size search up to {max_chunk_size}")
    print(f"🎯 Target coverage: {target_coverage*100:.1f}% of {total_samples} samples")
    print(f"🧠 Model max length: {model_max_len}, buffer: {buffer}")

    best_chunk_size = 1
    best_token_len = 0

    for chunk_size in range(1, max_chunk_size + 1):
        valid_count = 0
        token_lens = []
        max_len_this_chunk = 0

        for i in range(0, total_samples, chunk_size):
            chunk = contents[i : i + chunk_size]
            if not chunk:
                continue

            concat_text = "\n\n".join(chunk)
            prompt_text = generate_post_processing_prompt(concat_text)

            prompt = tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt_text}],
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=False,
            )

            token_len = get_token_len(prompt, tokenizer)
            token_lens.append(token_len)

            if token_len + buffer <= model_max_len:
                valid_count += len(chunk)
            max_len_this_chunk = max(max_len_this_chunk, token_len)

        coverage = valid_count / total_samples
        pct95 = sorted(token_lens)[int(0.95 * len(token_lens))]
        token_len_to_use = max_len_this_chunk + buffer

        print(
            f"🔎 Chunk size {chunk_size:2d} | "
            f"95% ≤ {pct95} | Max token len = {max_len_this_chunk} → "
            f"With buffer: {token_len_to_use} | "
            f"Coverage = {valid_count}/{total_samples} ({coverage:.2%})"
        )

        if coverage >= target_coverage and token_len_to_use <= model_max_len:
            best_chunk_size = chunk_size
            best_token_len = token_len_to_use
        else:
            print(f"⚠️  Skipping chunk size {chunk_size} due to insufficient coverage or token limit.")
            break

    print(
        f"\n✅ Selected chunk size: {best_chunk_size} with prompt length ≤ {best_token_len} "
        f"achieving ≥ {target_coverage*100:.1f}% coverage"
    )

    return best_chunk_size, best_token_len

def find_max_model_len_and_chunk_size(data: list[dict], model_path: str) -> tuple[int, int]:
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model_max_len = getattr(tokenizer, "model_max_length", 40960)
    return estimate_chunk_size_maximizing_coverage(
        data,
        tokenizer,
        model_max_len=model_max_len,
        buffer=200,
        max_chunk_size=20,
        target_coverage=0.98,
    )
