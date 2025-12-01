import pydantic
import yaml
from typing import Optional
from enum import StrEnum
from typing_extensions import Self
import transformers


class TrainerSteps(StrEnum):
    on_train_start = "on_train_start"
    on_step_start = "on_step_start"
    on_step_end = "on_step_end"
    on_exception = "on_exception"
    on_train_end = "on_train_end"


class OptimizerConfig(pydantic.BaseModel):
    name: str
    lr: float
    weight_decay: float = 0.0
    betas: tuple = (0.9, 0.999)
    eps: float = 1e-8


class SchedulerConfig(pydantic.BaseModel):
    name: str
    warmup_steps: int


class AcceleratorConfig(pydantic.BaseModel):
    gradient_accumulation_steps: int = 1
    mixed_precision: str = "fp16"


class WandbConfig(pydantic.BaseModel):
    project: str
    name: Optional[str] = None
    log_model: bool = False


class ModelConfig(pydantic.BaseModel):
    """Similar to pretrained config from transformers but with just required params."""

    model_name: str
    config_name: str
    hidden_size: int
    num_attention_heads: int
    num_key_value_heads: int
    num_hidden_layers: int
    intermediate_size: int
    max_position_embeddings: int
    tie_word_embeddings: bool

    @pydantic.model_validator(mode="after")
    def validate_model_and_config_name(self) -> Self:
        if self.model_name:
            if hasattr(transformers, self.model_name):
                model_class = getattr(transformers, self.model_name)
                if not issubclass(model_class, transformers.PreTrainedModel):
                    raise ValueError(
                        f"model_name '{self.model_name}' is not a valid PreTrainedModel class in transformers."
                    )
            else:
                raise ValueError(
                    f"model_name '{self.model_name}' not found in transformers library."
                )
        if self.config_name:
            if hasattr(transformers, self.config_name):
                config_class = getattr(transformers, self.config_name)
                if not issubclass(config_class, transformers.PretrainedConfig):
                    raise ValueError(
                        f"model_config '{self.config_name}' is not a valid PretrainedConfig class in transformers."
                    )
            else:
                raise ValueError(
                    f"model_config '{self.config_name}' not found in transformers library."
                )
        return self

    def _get_pretrained_config(self):
        """Instantiate the HF config using the Pydantic fields automatically."""
        config_class = getattr(transformers, self.config_name)

        # Dump all pydantic fields into a dict
        cfg_dict = self.model_dump()

        cfg_dict = {
            k: v for k, v in cfg_dict.items() if k not in {"model_name", "config_name"}
        }

        # Instantiate
        config = config_class(**cfg_dict)
        return config

    def _get_pretrained_model(self):
        config = self._get_pretrained_config()
        model_class = getattr(transformers, self.model_name)
        return model_class(config)


class TrainerState(pydantic.BaseModel):
    model_params: ModelConfig
    optimizer: OptimizerConfig
    scheduler: SchedulerConfig
    wandb_config: Optional[WandbConfig] = None
    max_steps: int
    batch_size: int
    accelerate_config: AcceleratorConfig
    log_every: int
    gradient_clip_value: float = 1.0
    eval_every: int = 1000
    seed: int = 42

    @classmethod
    def from_yaml(cls, path: str) -> "TrainerState":
        """Load TrainerState from a YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)
