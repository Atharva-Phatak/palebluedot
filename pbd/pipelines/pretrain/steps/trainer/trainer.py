from accelerate import Accelerator
from accelerate.utils import set_seed
from accelerate.logging import get_logger
import typing as T
import time
import torch
from pbd.pipelines.pretrain.steps.callbacks.metrics import MetricRunner
from pbd.pipelines.pretrain.steps.callbacks.base import Callback
import pbd.pipelines.pretrain.steps.trainer.state as state
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)


def get_learning_rates(optimizer):
    return {pg["name"]: pg["lr"] for pg in optimizer.param_groups if "name" in pg}


class PretrainTrainer:
    """Production-ready pretraining trainer with callback support."""

    def __init__(
        self,
        config_path: str,
        callbacks: T.Optional[list[Callback]] = None,
    ):
        self.trainer_state: state.TrainerState = state.TrainerState.from_yaml(
            config_path
        )
        # Set seed for reproducibility
        set_seed(self.trainer_state.seed)
        self.logger = get_logger("pretrain_trainer")

        self.gradient_clip_value: float = self.trainer_state.gradient_clip_value
        self.acc: Accelerator = Accelerator(
            **self.trainer_state.accelerate_config.dict()
        )

        # Log training configuration
        self.logger.info(
            f"Initializing trainer with {self.acc.num_processes} process(es)"
        )
        self.logger.info(
            f"Mixed precision: {self.trainer_state.accelerate_config.mixed_precision}"
        )
        self.logger.info(
            f"Gradient accumulation steps: {self.acc.gradient_accumulation_steps}"
        )
        self.logger.info(f"Max steps: {self.trainer_state.max_steps}")

        self.iter_loader = None
        self.dataloader_state = 0

        self.max_steps = self.trainer_state.max_steps
        self.global_step = 0
        self.log_every = self.trainer_state.log_every
        self.callbacks = callbacks or []
        self.seed = self.trainer_state.seed

        # Use MetricManager instead of MetricsTracker to work with callbacks

        self.metrics = MetricRunner()
        self.train_start_time = None

        # Training stability tracking
        self.num_nan_losses = 0
        self.max_nan_losses = 3

        self.model = self._load_model()
        self.train_loader = self._load_train_dataloader()
        self.val_loader = self._load_eval_dataloader()
        self.optimizer, self.scheduler = self._load_optimizer_and_scheduler()
        (
            self.model,
            self.optimizer,
            self.scheduler,
            self.train_loader,
            self.val_loader,
        ) = self.acc.prepare(
            self.model,
            self.optimizer,
            self.scheduler,
            self.train_loader,
            self.val_loader,
        )
        self._stage: str = None
        self._reset_dataloader()

        self.logger.info("Trainer initialization complete")

    def _load_model(self):
        """Load model architecture."""
        model = self.trainer_state.model_params._get_pretrained_model()
        return model

    def _load_train_dataloader(self) -> torch.utils.data.DataLoader:
        """Load training dataloader."""
        raise NotImplementedError

    def _load_eval_dataloader(self) -> torch.utils.data.DataLoader:
        """Load evaluation dataloader."""
        raise NotImplementedError

    def _load_optimizer_and_scheduler(
        self,
    ) -> tuple[torch.optim.Optimizer, torch.optim.lr_scheduler._LRScheduler]:
        """Load optimizer and scheduler."""
        raise NotImplementedError

    def _reset_dataloader(self):
        """Reset the dataloader iterator."""
        self.iter_loader = iter(self.train_loader)

    def _get_next_batch(self):
        """Get next batch and handle dataloader exhaustion."""
        try:
            batch = next(self.iter_loader)
            self.dataloader_state += 1
        except StopIteration:
            self.logger.warning("DataLoader exhausted, resetting...")
            self._reset_dataloader()
            batch = next(self.iter_loader)
            self.dataloader_state = 1
        return batch

    def _cb(self, name, *args, **kwargs):
        """Execute callback method on all registered callbacks."""
        for cb in self.callbacks:
            if hasattr(cb, name):
                getattr(cb, name)(self, *args, **kwargs)

    def _check_loss_validity(self, loss: torch.Tensor) -> bool:
        """Check if loss is valid (not NaN or Inf)."""
        if not torch.isfinite(loss).all():
            self.num_nan_losses += 1
            self.logger.warning(
                f"Loss is NaN or Inf at step {self.global_step}! "
                f"({self.num_nan_losses}/{self.max_nan_losses} strikes)"
            )
            if self.num_nan_losses >= self.max_nan_losses:
                self.logger.error(
                    f"Training stopped due to {self.max_nan_losses} NaN losses"
                )
                return False
        else:
            self.num_nan_losses = 0
        return True

    def forward(self, batch):
        """
        Must return: loss, tokens_processed
        Example: return outputs.loss, batch["input_ids"].numel()
        """
        outputs = self.model(**batch, labels=batch["input_ids"])
        loss = outputs.loss
        tokens_processed = batch["input_ids"].numel()
        return loss, tokens_processed

    def evaluate(self):
        """Run evaluation if eval_fn is provided."""
        self.logger.info(f"Running evaluation at step {self.global_step}")
        self.model.eval()
        avg_loss = 0.0
        num_batches = 0
        with torch.no_grad():
            for batch in self.val_loader:
                outputs = self.model(**batch, labels=batch["input_ids"])
                loss = outputs.loss
                avg_loss += loss.item()
                num_batches += 1
        avg_loss = avg_loss / max(1, num_batches)
        self.model.train()

        return avg_loss

    def load_checkpoint(self, checkpoint_path: str):
        """Load checkpoint and resume training."""
        self.logger.info(f"Loading checkpoint from {checkpoint_path}")
        checkpoint = torch.load(checkpoint_path, map_location=self.acc.device)

        unwrapped_model = self.acc.unwrap_model(self.model)
        unwrapped_model.load_state_dict(checkpoint["model_state_dict"])

        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.scheduler.load_state_dict(checkpoint["scheduler_state_dict"])

        self.global_step = checkpoint.get("global_step", 0)
        self.dataloader_state = checkpoint.get("dataloader_state", 0)

        # Fast-forward dataloader
        if self.dataloader_state > 0:
            self.logger.info(
                f"Fast-forwarding dataloader to batch {self.dataloader_state}"
            )
            self._reset_dataloader()
            for _ in range(self.dataloader_state):
                try:
                    _ = next(self.iter_loader)
                except StopIteration:
                    self._reset_dataloader()
                    break

        self.logger.info(
            f"Resumed from step {self.global_step}, dataloader at batch {self.dataloader_state}"
        )

    def _update_metrics(self, loss: float, tokens: int, step_time: float):
        """Update training metrics after each step."""
        self.metrics.update("loss", loss, self.trainer_state.batch_size)
        self.metrics.update("tokens_per_sec", tokens / step_time)

        learning_rate_per_group = get_learning_rates(self.optimizer)
        for name, lr in learning_rate_per_group.items():
            self.metrics.update(f"lr_{name}", lr)

    def fit(self):
        """Main training loop with callback support."""
        self.model.train()
        self.train_start_time = time.time()

        self.logger.info("=" * 80)
        self.logger.info(f"Starting training from step {self.global_step}")
        self.logger.info("=" * 80)

        self._cb(state.TrainerSteps.on_train_start.value)

        try:
            while self.global_step < self.max_steps:
                step_start_time = time.perf_counter()
                self._cb(state.TrainerSteps.on_step_start.value)

                batch = self._get_next_batch()

                # Training step with gradient accumulation
                with self.acc.accumulate(self.model):
                    loss, tokens = self.forward(batch)

                    # Check for NaN/Inf loss
                    if not self._check_loss_validity(loss):
                        self.logger.warning(
                            f"Stopping training at step {self.global_step} due to NaN loss"
                        )
                        break

                    self.acc.backward(loss)

                    # Gradient clipping
                    if self.acc.sync_gradients and self.gradient_clip_value is not None:
                        self.acc.clip_grad_value_(
                            self.model.parameters(), self.gradient_clip_value
                        )
                        # Track gradient norm
                        # if grad_norm is not None:
                        #   self.metrics.update("grad_norm", grad_norm)

                    self.optimizer.step()
                    self.optimizer.zero_grad()

                # Update scheduler
                self.scheduler.step()

                # Update metrics
                step_time = time.perf_counter() - step_start_time

                self._update_metrics(
                    loss=loss.item(), tokens=tokens, step_time=step_time
                )

                # Evaluation
                if (
                    self.trainer_state.eval_every
                    and self.global_step % self.trainer_state.eval_every == 0
                    and self.global_step > 0
                ):
                    val_loss = self.evaluate()
                    if val_loss is not None:
                        self.logger.info(
                            f"Evaluation: {val_loss}", main_process_only=True
                        )

                self.global_step += 1
                self._cb(state.TrainerSteps.on_step_end.value)

                # Logging
                if self.global_step % self.log_every == 0:
                    self._log_metrics()

        except KeyboardInterrupt:
            self.logger.warning("Training interrupted by user (Ctrl+C)")
            self.logger.info("Saving checkpoint before exit...")
            if self.acc.is_main_process:
                emergency_ckpt = Path("./checkpoints") / "checkpoint_interrupted.pt"
                self.save_checkpoint(str(emergency_ckpt))

        except Exception as e:
            self.logger.error(f"Training failed with error: {e}", exc_info=True)
            self._cb(state.TrainerSteps.on_exception.value, exception=e)
            raise

        finally:
            self._cb("on_train_end")

            # Final stats
            if self.train_start_time:
                total_time = time.time() - self.train_start_time
                self.logger.info("=" * 80)
                self.logger.info("Training completed!")
                self.logger.info(f"Total time: {total_time / 3600:.2f} hours")
                self.logger.info(
                    f"Average steps/sec: {self.global_step / total_time:.2f}"
                )
                self.logger.info("=" * 80)

    def _log_metrics(self):
        """Log current training metrics."""
        if not self.acc.is_local_main_process:
            return

        progress = self.global_step / self.max_steps * 100
        elapsed = time.time() - self.train_start_time
        steps_per_sec = self.global_step / elapsed if elapsed > 0 else 0
        eta = (
            (self.max_steps - self.global_step) / steps_per_sec
            if steps_per_sec > 0
            else 0
        )

        loss = self.metrics.get_avg("loss")
        tok_s = self.metrics.get_avg("tokens_per_sec")

        log_msg = (
            f"Step {self.global_step}/{self.max_steps} ({progress:.1f}%) | "
            f"loss: {loss:.4f} | "
            f"Tok/s: {tok_s:.0f} | "
            f"ETA: {eta / 3600:.2f}h"
        )

        self.logger.info(
            log_msg,
            main_process_only=True,
        )
        self.metrics.reset("tokens_per_sec")
        self.metrics.reset("loss")
