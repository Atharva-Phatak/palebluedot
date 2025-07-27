import os
from omegaconf import OmegaConf


def load_config():
    root_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )  # infrastructure/
    config_path = os.path.join(root_dir, "configs", "config.yaml")
    cfg = OmegaConf.load(config_path)
    return cfg
