import wandb
from pbd.pipelines.pretrain.steps.callbacks.base import Callback
import os


class WandbCallback(Callback):
    """Logs metrics to Weights & Biases with proper accelerate integration."""

    def __init__(
        self,
    ):
        _key = os.getenv("WANDB_API")
        wandb.login(key=_key)
        self.run = None

    def on_train_start(self, trainer):
        if trainer.acc.is_main_process:
            self.run = wandb.init(
                project=trainer.trainer_state.wandb_config.project,
                name=trainer.trainer_state.wandb_config.name,
                config=trainer.trainer_state.dict(),
                resume="allow",
            )
            trainer.logger.info(f"W&B run initialized: {self.run.name}")

    def on_step_start(self, trainer):
        pass

    def on_step_end(self, trainer):
        if trainer.acc.is_main_process:
            # Get all metrics
            metrics = trainer.metrics.tracked_metrics
            metrics["train/global_step"] = trainer.global_step

            wandb.log(metrics, step=trainer.global_step)

    def on_exception(self, trainer, e):
        """Log exception to W&B and mark run as failed."""
        if trainer.acc.is_main_process and self.run:
            trainer.logger.info("Logging exception to W&B")
            wandb.alert(
                title="Training Failed",
                text=f"Training failed at step {trainer.global_step}: {str(e)}",
                level=wandb.AlertLevel.ERROR,
            )

    def on_train_end(self, trainer):
        if trainer.acc.is_main_process:
            if trainer.trainer_state.wandb_config.log_model:
                trainer.logger.info("Saving final model to W&B")
                wandb.save("model_final.pt")
            wandb.finish()
            trainer.logger.info("W&B run finished")
