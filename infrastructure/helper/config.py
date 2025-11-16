import os
from omegaconf import OmegaConf
from infrastructure.helper.constants import InfrastructureConfig


def load_config() -> InfrastructureConfig:
    root_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )  # infrastructure/
    config_path = os.path.join(root_dir, "configs", "config.yaml")
    cfg = OmegaConf.load(config_path)
    # Convert DictConfig to dict and validate with Pydantic
    data = OmegaConf.to_container(cfg, resolve=True)
    return InfrastructureConfig(**data)
