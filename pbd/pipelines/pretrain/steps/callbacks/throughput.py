import time
from typing import Callable, Dict, Optional
import torch
from torch.utils.flop_counter import FlopCounterMode


class ThroughputCallback:
    """
    Comprehensive throughput monitoring with FLOPs and MFU calculation.
    Based on PyTorch Lightning's Throughput utility.
    """

    def __init__(
        self,
        window_size: int = 10,
        log_every: int = 20,
        flops_per_batch: Optional[int] = None,
    ):
        """
        Args:
            window_size: Number of batches to use for rolling average
            log_every: Log throughput every N steps
            flops_per_batch: Total FLOPs per batch (forward + backward).
                           Can be calculated using measure_flops_per_batch()
        """
        self.window_size = window_size
        self.log_every = log_every
        self.flops_per_batch = flops_per_batch

        # Timing windows
        self._times = []
        self._batches_seen = []
        self._samples_seen = []
        self._tokens_seen = []

        self._start_time = None

    def on_train_start(self, trainer):
        self._start_time = time.perf_counter()

        if trainer.acc.is_main_process:
            trainer.logger.info("Throughput monitoring started")
            if self.flops_per_batch:
                device_flops = self._get_device_flops(trainer.acc.device)
                if device_flops:
                    trainer.logger.info(
                        f"Device theoretical FLOPs: {device_flops / 1e12:.2f} TFLOPS"
                    )

    def on_step_start(self, trainer):
        self._step_start = time.perf_counter()

    def on_exception(self, trainer, exception):
        """Log final throughput stats on exception."""
        pass

    def on_step_end(self, trainer):
        # Record timing
        current_time = time.perf_counter() - self._start_time

        self._times.append(current_time)
        self._batches_seen.append(trainer.global_step)
        self._tokens_seen.append(
            trainer.metrics.step_tokens[-1] if trainer.metrics.step_tokens else 0
        )

        # Keep only window_size samples
        if len(self._times) > self.window_size:
            self._times.pop(0)
            self._batches_seen.pop(0)
            self._tokens_seen.pop(0)

        # Calculate throughput metrics
        if len(self._times) >= 2 and trainer.global_step % self.log_every == 0:
            metrics = self._compute_throughput(trainer)

            # Add to trainer metrics
            for key, value in metrics.items():
                trainer.metrics.add_metric(f"throughput/{key}", value)

            if trainer.acc.is_main_process:
                log_msg = (
                    f"Throughput - "
                    f"Samples/s: {metrics.get('samples_per_sec', 0):.1f} | "
                    f"Tokens/s: {metrics.get('tokens_per_sec', 0):.0f}"
                )
                if "flops_per_sec" in metrics:
                    log_msg += f" | TFLOPS: {metrics['flops_per_sec'] / 1e12:.2f}"
                if "mfu" in metrics:
                    log_msg += f" | MFU: {metrics['mfu'] * 100:.1f}%"

                trainer.logger.info(log_msg)

    def on_train_end(self, trainer):
        pass

    def _compute_throughput(self, trainer) -> Dict[str, float]:
        """Compute throughput metrics over the window."""
        if len(self._times) < 2:
            return {}

        # Time and batch differences
        time_delta = self._times[-1] - self._times[0]
        batches_delta = self._batches_seen[-1] - self._batches_seen[0]
        tokens_delta = sum(self._tokens_seen)

        metrics = {}

        if time_delta > 0:
            # Batches per second
            metrics["batches_per_sec"] = batches_delta / time_delta

            # Tokens per second (accounting for world size)
            world_size = trainer.acc.num_processes
            metrics["tokens_per_sec"] = (tokens_delta * world_size) / time_delta

            # Samples per second (if we track batch sizes separately)
            # For now, approximate with batches
            metrics["samples_per_sec"] = batches_delta / time_delta

            # FLOPs per second if we know FLOPs per batch
            if self.flops_per_batch:
                total_flops = self.flops_per_batch * batches_delta * world_size
                metrics["flops_per_sec"] = total_flops / time_delta

                # Model FLOPs Utilization (MFU)
                device_flops = self._get_device_flops(trainer.acc.device)
                if device_flops:
                    metrics["mfu"] = metrics["flops_per_sec"] / (
                        device_flops * world_size
                    )

        return metrics

    def _get_device_flops(self, device) -> Optional[float]:
        """Get theoretical FLOPs for the device."""
        if not torch.cuda.is_available():
            return None

        # Approximate TFLOPS for common GPUs (in FP16/BF16)
        # These are theoretical peaks, actual will be lower
        device_name = torch.cuda.get_device_name(device)

        flops_map = {
            "A100": 312e12,  # 312 TFLOPS (FP16)
            "H100": 989e12,  # 989 TFLOPS (FP16)
            "V100": 125e12,  # 125 TFLOPS (FP16)
            "A6000": 154e12,  # 154 TFLOPS (FP16)
            "4090": 165e12,  # 165 TFLOPS (FP16)
            "3090": 71e12,  # 71 TFLOPS (FP16)
        }

        for key, flops in flops_map.items():
            if key in device_name:
                return flops

        return None


def measure_flops_per_batch(
    model: torch.nn.Module,
    forward_fn: Callable,
    loss_fn: Optional[Callable] = None,
) -> int:
    """
    Utility to compute the total number of FLOPs per batch (forward + backward).

    Args:
        model: The model to measure
        forward_fn: A callable that runs forward pass and returns outputs.
                   Example: lambda: model(input_ids=input_ids, labels=labels)
        loss_fn: Optional function that computes loss given forward_fn output.
                If None, assumes forward_fn returns a loss or dict with 'loss' key.

    Returns:
        Total FLOPs per batch (forward + backward if loss_fn provided)

    Example:
        >>> with torch.device("meta"):
        >>>     model = GPT2LMHeadModel(config)
        >>>     input_ids = torch.randint(0, 50257, (32, 512))
        >>>     forward_fn = lambda: model(input_ids=input_ids, labels=input_ids)
        >>>     flops = measure_flops_per_batch(model, forward_fn)
    """

    flop_counter = FlopCounterMode(display=False)
    with flop_counter:
        if loss_fn is None:
            # Assume forward_fn returns loss or dict with loss
            output = forward_fn()
            if isinstance(output, dict) and "loss" in output:
                loss = output["loss"]
            elif hasattr(output, "loss"):
                loss = output.loss
            else:
                loss = output
            loss.backward()
        else:
            # User provided custom loss function
            output = forward_fn()
            loss = loss_fn(output)
            loss.backward()

    total_flops = flop_counter.get_total_flops()
    return total_flops
