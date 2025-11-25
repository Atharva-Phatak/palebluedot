class GradientStatsCallback:
    """
    Monitors gradient statistics including norm and per-layer analysis.
    Helps detect training instabilities early.
    """

    def __init__(self, log_every: int = 100, log_per_layer: bool = False):
        self.log_every = log_every
        self.log_per_layer = log_per_layer

    def on_train_start(self, trainer):
        pass

    def on_step_start(self, trainer):
        pass

    def on_step_end(self, trainer):
        if trainer.global_step % self.log_every == 0:
            total_norm = 0.0
            num_params = 0
            max_grad = 0.0
            min_grad = float("inf")

            for p in trainer.model.parameters():
                if p.grad is not None:
                    param_norm = p.grad.data.norm(2)
                    total_norm += param_norm.item() ** 2
                    num_params += 1

                    # Track min/max gradients
                    max_grad = max(max_grad, p.grad.data.abs().max().item())
                    min_grad = min(min_grad, p.grad.data.abs().min().item())

            if num_params > 0:
                total_norm = total_norm**0.5
                trainer.metrics.add_metric("gradients/norm", total_norm)
                trainer.metrics.add_metric("gradients/max", max_grad)
                trainer.metrics.add_metric("gradients/min", min_grad)

                if trainer.acc.is_main_process and self.log_per_layer:
                    trainer.logger.info(
                        f"Gradient stats - Norm: {total_norm:.4f} | "
                        f"Max: {max_grad:.2e} | Min: {min_grad:.2e}"
                    )

    def on_train_end(self, trainer):
        pass
