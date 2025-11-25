from datasets import Dataset, concatenate_datasets
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def dataset_mixer_hybrid_sharded(
    datasets: list[Dataset],
    dataset_names: list[str],
    num_shards: int,
    weights: list[float] = None,
    shuffle: bool = True,
    seed: int = 42,
):
    """
    Mix datasets using ALL data with hybrid strategy:
    - Early shards maintain the mixture ratio
    - Later shards use remaining data from larger datasets

    Example:
        ds1=970K rows, ds2=186K rows, weights=[0.5, 0.5], num_shards=10
        Result: Shards 0-2 have 50-50 mix, Shards 3-9 have only ds1
                ALL 1.1M rows are used across 10 shards

    Args:
        datasets: List of datasets to mixilm/it-welcome-to-derry-season-1-1630860104/
        num_shards: Number of shards to create
        weights: Target mixture ratios (e.g., [0.5, 0.3, 0.2])
        shuffle: Whether to shuffle data
        seed: Random seed for reproducibility

    Returns:
        List of sharded datasets (ALL data preserved)
    """
    # Step 1: Setup - normalize weights and shuffle if needed
    if weights is None:
        weights = [1.0] * len(datasets)

    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]  # Normalize to sum to 1.0
    datasets = [ds.select_columns(["text"]) for ds in datasets]
    if shuffle:
        datasets = [ds.shuffle(seed=seed) for ds in datasets]

    # Step 2: Find bottleneck - which dataset runs out first given the weights?
    # Example: ds1=1000 rows with weight=0.5 → can support 2000 total rows
    #          ds2=300 rows with weight=0.5 → can support 600 total rows (BOTTLENECK)
    max_sizes = [
        len(ds) / weight for ds, weight in zip(datasets, weights) if weight > 0
    ]
    mixed_size = int(min(max_sizes))  # Maximum rows we can get with proper ratio

    logger.info(f"Weights: {weights}")
    logger.info(f"Mixed portion: {mixed_size:,} rows (maintains {weights} ratio)")

    # Step 3: Create mixed portion - sample from each dataset according to weights
    mixed_parts = []
    rows_used = []

    for i, (ds, weight) in enumerate(zip(datasets, weights)):
        sample_size = int(mixed_size * weight)
        mixed_parts.append(ds.select(range(sample_size)))
        rows_used.append(sample_size)
        logger.info(
            f"  Dataset {dataset_names[i]}: using {sample_size:,}/{len(ds):,} rows"
        )

    # Combine and shuffle the mixed portion
    mixed_data = concatenate_datasets(mixed_parts)
    if shuffle:
        mixed_data = mixed_data.shuffle(seed=seed)

    # Step 4: Collect remaining data - everything we didn't use yet
    remaining_parts = []

    for i, ds in enumerate(datasets):
        leftover = len(ds) - rows_used[i]
        if leftover > 0:
            remaining_parts.append(ds.select(range(rows_used[i], len(ds))))
            logger.info(f"  Dataset {dataset_names[i]}: {leftover:,} rows remaining")

    # Combine remaining data if any exists
    if remaining_parts:
        remaining_data = concatenate_datasets(remaining_parts)
        if shuffle:
            remaining_data = remaining_data.shuffle(seed=seed + 1)
        logger.info(f"Remaining portion: {len(remaining_data):,} rows")
    else:
        remaining_data = None

    # Step 5: Split everything into shards
    # Allocate shards proportionally between mixed and remaining data
    total_rows = len(mixed_data) + (len(remaining_data) if remaining_data else 0)
    num_mixed_shards = max(1, round(num_shards * len(mixed_data) / total_rows))
    num_remaining_shards = num_shards - num_mixed_shards

    shards = []

    # Shard the mixed data
    shards.extend(_split_into_shards(mixed_data, num_mixed_shards))

    # Shard the remaining data
    if remaining_data and num_remaining_shards > 0:
        shards.extend(_split_into_shards(remaining_data, num_remaining_shards))

    # Verify we didn't lose any data
    total_sharded = sum(len(s) for s in shards)
    total_original = sum(len(ds) for ds in datasets)
    assert total_sharded == total_original, (
        f"Data loss! {total_original:,} → {total_sharded:,}"
    )

    logger.info(f"✅ Created {len(shards)} shards with ALL {total_original:,} rows")
    logger.info(f"   Sizes: {[len(s) for s in shards]}")

    return shards


def _split_into_shards(dataset: Dataset, num_shards: int) -> list[Dataset]:
    """
    Helper: Split a dataset into equal-sized shards using HF's built-in method.

    Uses the efficient .shard() method which is optimized for large datasets.
    Example: 1000 rows, 3 shards → [334, 333, 333]
    """
    return [dataset.shard(num_shards=num_shards, index=i) for i in range(num_shards)]


def verify_hybrid_shards(datasets: list[Dataset], shards: list[Dataset]) -> dict:
    """
    Verify that ALL original data is present in shards.

    Returns dict with verification results.
    """
    total_original = sum(len(ds) for ds in datasets)
    total_sharded = sum(len(s) for s in shards)
    all_preserved = total_original == total_sharded

    logger.info("=" * 60)
    logger.info("VERIFICATION")
    logger.info("=" * 60)

    if all_preserved:
        logger.info(f"✅ ALL DATA PRESERVED: {total_original:,} rows")
    else:
        logger.error(f"❌ DATA LOSS: {total_original:,} → {total_sharded:,} rows")

    logger.info(f"   Number of shards: {len(shards)}")
    logger.info(f"   Shard sizes: {[len(s) for s in shards]}")
    logger.info("=" * 60)

    return {
        "original_total": total_original,
        "sharded_total": total_sharded,
        "all_preserved": all_preserved,
        "num_shards": len(shards),
        "shard_sizes": [len(s) for s in shards],
    }


def print_capacity_report(
    datasets: list[Dataset], dataset_names: list[str], weights: list[float] = None
):
    """
    Show how much data you can get with given weights.
    Identifies which dataset is the bottleneck.
    """
    if weights is None:
        weights = [1.0] * len(datasets)

    # Normalize weights
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]

    # Find bottleneck
    max_sizes = []
    for ds, weight in zip(datasets, weights):
        if weight > 0:
            max_sizes.append(len(ds) / weight)
        else:
            max_sizes.append(float("inf"))

    max_total = int(min(max_sizes))
    bottleneck_idx = max_sizes.index(min(max_sizes))

    logger.info("=" * 70)
    logger.info("CAPACITY REPORT")
    logger.info("=" * 70)
    logger.info(f"Weights: {weights}")
    logger.info(f"Maximum mixed portion: {max_total:,} rows")
    logger.info(f"Bottleneck: Dataset {bottleneck_idx + 1}")
    logger.info("")
    logger.info("-" * 70)
    logger.info(
        f"{'Dataset':<10} {'Total':>15} {'Mixed':>15} {'Remaining':>15} {'Usage':>10}"
    )
    logger.info("-" * 70)

    total_all = 0
    total_mixed = 0
    total_remaining = 0

    for i, (ds, weight) in enumerate(zip(datasets, weights)):
        size = len(ds)
        mixed = int(max_total * weight)
        remaining = size - mixed
        usage = f"{(mixed / size) * 100:.1f}%"
        marker = " 🔴" if i == bottleneck_idx else ""

        logger.info(
            f"Dataset {dataset_names[i]} {size:>15,} {mixed:>15,} {remaining:>15,} {usage:>10}{marker}"
        )

        total_all += size
        total_mixed += mixed
        total_remaining += remaining

    logger.info("-" * 70)
    logger.info(
        f"{'TOTAL':<10} {total_all:>15,} {total_mixed:>15,} {total_remaining:>15,}"
    )
    logger.info("=" * 70)
    logger.info(
        f"You'll get {total_mixed:,} rows with proper ratio + {total_remaining:,} leftover"
    )
    logger.info(f"Grand total: {total_all:,} rows (100% data utilization)")
    logger.info("=" * 70)
