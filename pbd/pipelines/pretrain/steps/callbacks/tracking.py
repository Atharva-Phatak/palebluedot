from typing import Optional
import wandb


class WandbCallback:
    """Logs metrics to Weights & Biases with proper accelerate integration."""

    def __init__(
        self,
        project: str,
        name: Optional[str] = None,
        config: Optional[dict] = None,
        log_model: bool = False,
        **wandb_kwargs,
    ):
        self.project = project
        self.name = name
        self.config = config
        self.log_model = log_model
        self.wandb_kwargs = wandb_kwargs
        self.run = None

    def on_train_start(self, trainer):
        if trainer.acc.is_main_process:
            self.run = wandb.init(
                project=self.project,
                name=self.name,
                config=self.config,
                resume="allow",
                **self.wandb_kwargs,
            )
            trainer.logger.info(f"W&B run initialized: {self.run.name}")

    def on_step_start(self, trainer):
        pass

    def on_step_end(self, trainer):
        if trainer.acc.is_main_process:
            # Get all metrics
            metrics = trainer.metrics.get_all_metrics()
            metrics["train/loss_ema"] = trainer.loss_ema
            metrics["train/global_step"] = trainer.global_step

            # Rename for W&B
            wandb_metrics = {
                f"train/{k}"
                if not k.startswith(("train/", "eval/", "system/"))
                else k: v
                for k, v in metrics.items()
            }

            wandb.log(wandb_metrics, step=trainer.global_step)

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
            if self.log_model:
                trainer.logger.info("Saving final model to W&B")
                wandb.save("model_final.pt")
            wandb.finish()
            trainer.logger.info("W&B run finished")
