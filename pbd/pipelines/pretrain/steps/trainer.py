from accelerate import Accelerator
from accelerate.utils import set_seed
from accelerate.logging import get_logger
import torch
import time
from pathlib import Path
import json
from pbd.pipelines.pretrain.steps.callbacks.metrics import MetricsTracker
from pbd.pipelines.pretrain.steps.exception import NaNException
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)


class PretrainTrainer:
    """Production-ready pretraining trainer with proper logging and state management."""

    def __init__(
        self,
        model,
        optimizer,
        scheduler,
        train_loader,
        *,
        max_steps=10_000,
        gradient_accumulation_steps=1,
        callbacks=None,
        accelerator_kwargs=None,
        log_every=20,
        gradient_clip_norm=1.0,
        mixed_precision=None,
        eval_fn=None,
        eval_every=1000,
        seed=42,
    ):
        # Set seed for reproducibility
        set_seed(seed)
        self.logger = get_logger("pretrain_trainer")
        # Set up accelerator with gradient clipping
        accelerator_kwargs = accelerator_kwargs or {}
        # if gradient_clip_norm is not None:
        #   accelerator_kwargs["gradient_clip_val"] = gradient_clip_norm
        self.gradient_clip_norm = gradient_clip_norm
        self.acc = Accelerator(
            gradient_accumulation_steps=gradient_accumulation_steps,
            mixed_precision=mixed_precision,
            **accelerator_kwargs,
        )

        # Log training configuration
        self.logger.info(
            f"Initializing trainer with {self.acc.num_processes} process(es)"
        )
        self.logger.info(f"Mixed precision: {mixed_precision}")
        self.logger.info(f"Gradient accumulation steps: {gradient_accumulation_steps}")
        self.logger.info(f"Max steps: {max_steps:,}")

        (
            self.model,
            self.optimizer,
            self.scheduler,
            self.train_loader,
        ) = self.acc.prepare(model, optimizer, scheduler, train_loader)

        self.iter_loader = None
        self.dataloader_state = 0  # Track number of batches consumed
        self._reset_dataloader()

        self.max_steps = max_steps
        self.global_step = 0
        self.log_every = log_every
        self.callbacks = callbacks or []
        self.gradient_clip_norm = gradient_clip_norm
        self.eval_fn = eval_fn
        self.eval_every = eval_every
        self.seed = seed

        # Metrics tracking
        self.metrics = MetricsTracker()
        self.train_start_time = None

        # Loss EMA
        self.loss_ema = None
        self.ema_beta = 0.99

        # Training stability tracking
        self.num_nan_losses = 0
        self.max_nan_losses = 3  # Stop training after this many NaN losses

        self.logger.info("Trainer initialization complete")

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

    # ---------------------------------------------------
    # Inject callbacks
    # ---------------------------------------------------
    def _cb(self, name, *args, **kwargs):
        for cb in self.callbacks:
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
            self.num_nan_losses = 0  # Reset counter on valid loss
        return True

    # ---------------------------------------------------
    # Custom loss function (to be implemented by subclass)
    # ---------------------------------------------------
    def forward(self, batch):
        """
        Must return: loss, tokens_processed
        Example: return outputs.loss, batch["input_ids"].numel()
        """
        raise NotImplementedError

    # ---------------------------------------------------
    # Evaluation
    # ---------------------------------------------------
    def evaluate(self):
        """Run evaluation if eval_fn is provided."""
        if self.eval_fn is None:
            return None

        self.logger.info(f"Running evaluation at step {self.global_step}")
        self.model.eval()
        with torch.no_grad():
            eval_metrics = self.eval_fn(self.model, self.acc)
        self.model.train()

        return eval_metrics

    # ---------------------------------------------------
    # Checkpoint management
    # ---------------------------------------------------
    def save_checkpoint(self, checkpoint_path: str):
        """Save full training state including dataloader position."""
        if not self.acc.is_main_process:
            return

        checkpoint_path = Path(checkpoint_path)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        # Prepare checkpoint dictionary
        checkpoint = {
            "global_step": self.global_step,
            "dataloader_state": self.dataloader_state,
            "model_state_dict": self.acc.unwrap_model(self.model).state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict(),
            "scheduler_state_dict": self.scheduler.state_dict(),
            "loss": self.metrics.latest_loss,
            "loss_ema": self.loss_ema,
            "metrics": self.metrics.to_dict(),
            "seed": self.seed,
            "config": {
                "max_steps": self.max_steps,
                "gradient_accumulation_steps": self.acc.gradient_accumulation_steps,
                "gradient_clip_norm": self.gradient_clip_norm,
            },
        }

        # Save checkpoint
        torch.save(checkpoint, checkpoint_path)
        self.logger.info(f"Checkpoint saved to {checkpoint_path}")

        # Save metadata as JSON for easy inspection
        metadata_path = checkpoint_path.parent / f"{checkpoint_path.stem}_metadata.json"
        metadata = {
            "global_step": self.global_step,
            "loss": self.metrics.latest_loss,
            "loss_ema": self.loss_ema,
            "tokens_per_second": self.metrics.tokens_per_s,
        }
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def load_checkpoint(self, checkpoint_path: str):
        """Load checkpoint and resume training from exact state."""
        self.logger.info(f"Loading checkpoint from {checkpoint_path}")
        checkpoint = torch.load(checkpoint_path, map_location=self.acc.device)

        # Load model state
        unwrapped_model = self.acc.unwrap_model(self.model)
        unwrapped_model.load_state_dict(checkpoint["model_state_dict"])

        # Load optimizer and scheduler
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.scheduler.load_state_dict(checkpoint["scheduler_state_dict"])

        # Restore global step and dataloader state
        self.global_step = checkpoint.get("global_step", 0)
        self.dataloader_state = checkpoint.get("dataloader_state", 0)
        self.loss_ema = checkpoint.get("loss_ema", None)

        # Restore metrics if available
        if "metrics" in checkpoint:
            self.metrics.from_dict(checkpoint["metrics"])

        # Fast-forward dataloader to correct position
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

    # ---------------------------------------------------
    # Main trainer loop
    # ---------------------------------------------------
    def fit(self):
        """Main training loop with improved error handling."""
        self.model.train()
        self.train_start_time = time.time()

        self.logger.info("=" * 80)
        self.logger.info(f"Starting training from step {self.global_step}")
        self.logger.info("=" * 80)

        self._cb("on_train_start")

        try:
            while self.global_step < self.max_steps:
                step_start_time = time.perf_counter()
                self._cb("on_step_start")

                batch = self._get_next_batch()

                # Training step with gradient accumulation
                with self.acc.accumulate(self.model):
                    loss, tokens = self.forward(batch)

                    # Check for NaN/Inf loss
                    if not self._check_loss_validity(loss):
                        self._cb(
                            "on_exception",
                            exception=NaNException(
                                f"NaN loss at step {self.global_step}"
                            ),
                        )
                        self.logger.warning(
                            f"Stopping training at step {self.global_step} due to NaN loss"
                        )
                        break  # Exit training loop

                    self.acc.backward(loss)

                    # Gradient clipping (if not handled by accelerator)
                    if self.acc.sync_gradients and self.gradient_clip_norm:
                        self.acc.clip_grad_norm_(
                            self.model.parameters(), self.gradient_clip_norm
                        )

                    self.optimizer.step()
                    self.optimizer.zero_grad()

                # Update scheduler (outside accumulation context)
                self.scheduler.step()

                # Update metrics
                step_time = time.perf_counter() - step_start_time
                self.metrics.update(
                    loss=loss.item(),
                    tokens=tokens,
                    step_time=step_time,
                    learning_rate=self.optimizer.param_groups[0]["lr"],
                )

                # Update loss EMA
                if self.loss_ema is None:
                    self.loss_ema = self.metrics.latest_loss
                else:
                    self.loss_ema = (
                        self.ema_beta * self.loss_ema
                        + (1 - self.ema_beta) * self.metrics.latest_loss
                    )

                # Logging
                if self.global_step % self.log_every == 0:
                    self._log_metrics()

                # Evaluation
                if (
                    self.eval_every
                    and self.global_step % self.eval_every == 0
                    and self.global_step > 0
                ):
                    eval_metrics = self.evaluate()
                    if eval_metrics:
                        self.logger.info(
                            f"Evaluation: {eval_metrics}", main_process_only=True
                        )
                        # Add eval metrics to tracker
                        for key, value in eval_metrics.items():
                            self.metrics.add_metric(f"eval/{key}", value)

                self.global_step += 1
                self._cb("on_step_end")

        except KeyboardInterrupt:
            self.logger.warning("Training interrupted by user (Ctrl+C)")
            self._cb(
                "on_exception", exception=KeyboardInterrupt("User interrupted training")
            )
            self.logger.info("Saving checkpoint before exit...")
            # Save emergency checkpoint
            if self.acc.is_main_process:
                emergency_ckpt = Path("./checkpoints") / "checkpoint_interrupted.pt"
                self.save_checkpoint(str(emergency_ckpt))

        except Exception as e:
            self.logger.error(f"Training failed with error: {e}", exc_info=True)
            self._cb("on_exception", exception=e)
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
                self.logger.info(f"Final loss: {self.metrics.latest_loss:.4f}")
                self.logger.info(f"Final loss EMA: {self.loss_ema:.4f}")
                self.logger.info(f"Final perplexity: {self.metrics.perplexity:.2f}")
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

        self.logger.info(
            f"Step {self.global_step}/{self.max_steps} ({progress:.1f}%) | "
            f"Loss: {self.metrics.latest_loss:.4f} | "
            f"Loss EMA: {self.loss_ema:.4f} | "
            f"PPL: {self.metrics.perplexity:.2f} | "
            f"LR: {self.metrics.learning_rate:.2e} | "
            f"Tok/s: {self.metrics.tokens_per_s:.0f} | "
            f"ETA: {eta / 3600:.2f}h",
        )
