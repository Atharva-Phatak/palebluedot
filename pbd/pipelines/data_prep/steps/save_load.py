import logging
from datasets import Dataset, load_from_disk
import os

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def save_shards_to_disk(
    shards: list[Dataset],
    output_dir: str,
    shard_name_template: str = "shard_{index:04d}",
):
    """
    Save shards to disk using HuggingFace's save_to_disk method.

    Each shard is saved in its own subdirectory for easy loading later.

    Args:
        shards: List of dataset shards to save
        output_dir: Base directory to save shards (e.g., "./my_dataset")
        shard_name_template: Template for shard names (must include {index})
                           Default: "shard_{index:04d}" → shard_0000, shard_0001, etc.

    Example:
        >>> shards = dataset_mixer_hybrid_sharded([ds1, ds2], num_shards=10, weights=[0.5, 0.5])
        >>> save_shards_to_disk(shards, "./data/mixed_dataset")

        Creates structure:
        ./data/mixed_dataset/
            ├── shard_0000/
            ├── shard_0001/
            ├── ...
            └── shard_0009/
    """

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    logger.info(f"Saving {len(shards)} shards to {output_dir}")

    for i, shard in enumerate(shards):
        shard_name = shard_name_template.format(index=i)
        shard_path = os.path.join(output_dir, shard_name)

        logger.info(f"  Saving {shard_name}: {len(shard):,} rows → {shard_path}")
        shard.save_to_disk(shard_path)

    logger.info(f"✅ All shards saved to {output_dir}")

    # Save metadata file with info about shards
    metadata_path = os.path.join(output_dir, "metadata.txt")
    with open(metadata_path, "w") as f:
        f.write(f"Number of shards: {len(shards)}\n")
        f.write(f"Total rows: {sum(len(s) for s in shards):,}\n")
        f.write("\nShard details:\n")
        for i, shard in enumerate(shards):
            shard_name = shard_name_template.format(index=i)
            f.write(f"  {shard_name}: {len(shard):,} rows\n")

    logger.info(f"📝 Metadata saved to {metadata_path}")


def load_shards_from_disk(
    input_dir: str,
    shard_name_template: str = "shard_{index:04d}",
    num_shards: int = None,
) -> list[Dataset]:
    """
    Load shards from disk that were saved with save_shards_to_disk.

    Args:
        input_dir: Base directory containing shards
        shard_name_template: Template used when saving (must include {index})
        num_shards: Number of shards to load. If None, auto-detects by scanning directory.

    Returns:
        List of loaded dataset shards

    Example:
        >>> shards = load_shards_from_disk("./data/mixed_dataset")
        >>> # Use for training
        >>> for shard in shards:
        >>>     train_on_shard(shard)
    """

    # Auto-detect number of shards if not specified
    if num_shards is None:
        # Count directories matching the pattern
        all_items = os.listdir(input_dir)
        shard_dirs = [
            d
            for d in all_items
            if os.path.isdir(os.path.join(input_dir, d))
            and d.startswith(shard_name_template.split("{")[0])
        ]
        num_shards = len(shard_dirs)
        logger.info(f"Auto-detected {num_shards} shards in {input_dir}")

    shards = []
    logger.info(f"Loading {num_shards} shards from {input_dir}")

    for i in range(num_shards):
        shard_name = shard_name_template.format(index=i)
        shard_path = os.path.join(input_dir, shard_name)

        if not os.path.exists(shard_path):
            logger.error(f"❌ Shard not found: {shard_path}")
            raise FileNotFoundError(f"Shard {shard_name} not found at {shard_path}")

        logger.info(f"  Loading {shard_name} from {shard_path}")
        shard = load_from_disk(shard_path)
        shards.append(shard)
        logger.debug(f"    Loaded {len(shard):,} rows")

    total_rows = sum(len(s) for s in shards)
    logger.info(f"✅ Loaded {len(shards)} shards with {total_rows:,} total rows")

    return shards
