from pathlib import Path
from typing import Optional


class CheckpointCallback:
    """Saves model checkpoints at specified intervals with full state preservation."""

    def __init__(
        self,
        save_dir: str,
        save_every: int = 1000,
        keep_last_n: Optional[int] = 3,
        save_on_best: bool = False,
        metric_name: str = "loss_ema",
        mode: str = "min",
        save_on_exception: bool = True,
    ):
        self.save_dir = Path(save_dir)
        self.save_every = save_every
        self.keep_last_n = keep_last_n
        self.save_on_best = save_on_best
        self.metric_name = metric_name
        self.mode = mode
        self.save_on_exception = save_on_exception
        self.checkpoints = []
        self.best_metric = float("inf") if mode == "min" else float("-inf")

    def on_train_start(self, trainer):
        if trainer.acc.is_main_process:
            self.save_dir.mkdir(parents=True, exist_ok=True)
            trainer.logger.info(f"Checkpoints will be saved to {self.save_dir}")

    def on_step_start(self, trainer):
        pass

    def on_step_end(self, trainer):
        # Regular checkpoint saving
        if trainer.global_step % self.save_every == 0 and trainer.global_step > 0:
            ckpt_path = self.save_dir / f"checkpoint_step_{trainer.global_step}.pt"
            trainer.save_checkpoint(ckpt_path)

            # Track for cleanup
            self.checkpoints.append(ckpt_path)

            # Remove old checkpoints if needed
            if self.keep_last_n and len(self.checkpoints) > self.keep_last_n:
                old_ckpt = self.checkpoints.pop(0)
                if old_ckpt.exists():
                    old_ckpt.unlink()
                    trainer.logger.info(f"Removed old checkpoint: {old_ckpt.name}")

        # Save on best metric
        if self.save_on_best and trainer.acc.is_main_process:
            current_metric = getattr(trainer, self.metric_name, None)
            if current_metric is not None:
                is_best = (
                    self.mode == "min" and current_metric < self.best_metric
                ) or (self.mode == "max" and current_metric > self.best_metric)
                if is_best:
                    self.best_metric = current_metric
                    ckpt_path = self.save_dir / "checkpoint_best.pt"
                    trainer.save_checkpoint(ckpt_path)
                    trainer.logger.info(
                        f"New best {self.metric_name}: {current_metric:.4f}"
                    )

    def on_exception(self, trainer, exception):
        """Save emergency checkpoint on exception."""
        if self.save_on_exception and trainer.acc.is_main_process:
            trainer.logger.info("Saving emergency checkpoint due to exception...")
            ckpt_path = (
                self.save_dir / f"checkpoint_exception_step_{trainer.global_step}.pt"
            )
            trainer.save_checkpoint(ckpt_path)
            trainer.logger.info(f"Emergency checkpoint saved to {ckpt_path}")

    def on_train_end(self, trainer):
        # Save final checkpoint
        ckpt_path = self.save_dir / "checkpoint_final.pt"
        trainer.save_checkpoint(ckpt_path)
