from typing import Any, Dict
import torch


class MetricsTracker:
    """Centralized metrics tracking for training."""

    def __init__(self, window_size: int = 10):
        self.window_size = window_size

        # Current metrics
        self.latest_loss = 0.0
        self.learning_rate = 0.0
        self.tokens_per_s = 0.0
        self.perplexity = 0.0

        # For moving averages
        self.step_times = []
        self.step_tokens = []

        # Additional metrics storage
        self.extra_metrics = {}

    def update(self, loss: float, tokens: int, step_time: float, learning_rate: float):
        """Update metrics after each training step."""
        self.latest_loss = loss
        self.learning_rate = learning_rate

        # Update throughput
        self.step_times.append(step_time)
        self.step_tokens.append(tokens)

        if len(self.step_times) > self.window_size:
            self.step_times.pop(0)
            self.step_tokens.pop(0)

        if len(self.step_times) > 0:
            total_time = sum(self.step_times)
            total_tokens = sum(self.step_tokens)
            self.tokens_per_s = total_tokens / total_time if total_time > 0 else 0

        # Calculate perplexity
        self.perplexity = torch.exp(torch.tensor(loss)).item()

    def add_metric(self, name: str, value: float):
        """Add custom metric."""
        self.extra_metrics[name] = value

    def get_all_metrics(self) -> Dict[str, float]:
        """Get all current metrics as dictionary."""
        metrics = {
            "loss": self.latest_loss,
            "learning_rate": self.learning_rate,
            "tokens_per_second": self.tokens_per_s,
            "perplexity": self.perplexity,
        }
        metrics.update(self.extra_metrics)
        return metrics

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metrics state for checkpointing."""
        return {
            "latest_loss": self.latest_loss,
            "learning_rate": self.learning_rate,
            "tokens_per_s": self.tokens_per_s,
            "perplexity": self.perplexity,
            "extra_metrics": self.extra_metrics,
        }

    def from_dict(self, state: Dict[str, Any]):
        """Restore metrics state from checkpoint."""
        self.latest_loss = state.get("latest_loss", 0.0)
        self.learning_rate = state.get("learning_rate", 0.0)
        self.tokens_per_s = state.get("tokens_per_s", 0.0)
        self.perplexity = state.get("perplexity", 0.0)
        self.extra_metrics = state.get("extra_metrics", {})
