import pbd.pipelines.data_prep.steps.data_mixer as data_mixer
import pbd.pipelines.data_prep.steps.save_load as io
from omegaconf import OmegaConf
from datasets import load_dataset
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_yaml():
    return OmegaConf.load("configs/data_prep/datasets.yaml")


def load_datasets(dataset_names):
    datasets = []
    for name in dataset_names:
        ds = load_dataset(name, split="train")
        datasets.append(ds)
    return datasets


def generate_datasets():
    cfg = load_yaml()
    datasets = load_datasets(cfg.datasets)
    logger.info(f"✅ Loaded {len(datasets)} datasets:")
    data_mixer.print_capacity_report(datasets, dataset_names=cfg.datasets)
    shards = data_mixer.dataset_mixer_hybrid_sharded(
        datasets,
        dataset_names=cfg.datasets,
        num_shards=4,
        weights=cfg.weights,
        shuffle=True,
        seed=42,
    )
    data_mixer.verify_hybrid_shards(shards, datasets)
    logger.info(f"✅ Generated {len(shards)} mixed shards.")
    io.save_shards_to_disk(
        shards,
        output_dir="pbd/pipelines/data_prep/data",
        shard_name_template="shard_{index:04d}",
    )


if __name__ == "__main__":
    generate_datasets()
