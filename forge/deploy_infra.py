import os
import json
import logging
import re
import signal
import sys
import atexit
from datetime import datetime

from rich.console import Console
from dotenv import load_dotenv
import pulumi.automation as auto
import traceback

# Load secrets
secret_path: str = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".secrets")
)
load_dotenv(os.path.join(secret_path, ".env"))


class InfraDeployer:
    def __init__(
        self,
        stack_name: str,
        operation: str,
        passphrase: str = None,
        log_file: str = None,
        verbose: bool = False,
    ):
        self.stack_name = stack_name
        self.operation = operation
        self.passphrase = passphrase
        self.log_file = log_file
        self.verbose = verbose
        self.console = Console()
        self._stack = None

        atexit.register(self.cleanup)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        self._setup_logging()

        self._infra_base_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "infra")
        )

        try:
            if not self.passphrase:
                self.passphrase = "password"
                os.environ["PULUMI_CONFIG_PASSPHRASE"] = self.passphrase
            elif not os.environ.get("PULUMI_CONFIG_PASSPHRASE") and not os.environ.get(
                "PULUMI_CONFIG_PASSPHRASE_FILE"
            ):
                raise ValueError("Pulumi passphrase is required but not provided")

            if not os.path.exists(self._infra_base_path):
                raise FileNotFoundError(
                    f"Infrastructure base path {self._infra_base_path} does not exist."
                )

        except Exception as e:
            self.log_and_print(
                f"[red]Initialization error: {str(e)}[/red]", level="error", exc=e
            )
            raise

        self.log_and_print(
            f"[bold blue]InfraDeployer initialized with stack: {self.stack_name}, operation: {self.operation}[/bold blue]",
            level="info",
        )

    def _setup_logging(self):
        log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
        os.makedirs(log_dir, exist_ok=True)

        if not self.log_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_file = os.path.join(
                log_dir, f"infra_errors_{self.stack_name}_{timestamp}.log"
            )

        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(logging.Formatter("%(message)s"))

        self.logger = logging.getLogger(f"InfraDeployer.{self.stack_name}")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)
        self.logger.propagate = False

    def log_and_print(self, message: str, level: str = "info", exc: Exception = None):
        clean_message = re.sub(r"\[/?[^\]]*\]", "", message)

        if level == "error":
            if exc:
                clean_message += f"\n{traceback.format_exc()}"
            self.logger.error(clean_message)
            for handler in self.logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.flush()

        elif level == "warning":
            self.logger.warning(clean_message)

        elif level == "info":
            self.logger.info(clean_message)

        # Print to console always
        self.console.print(message)

    def _log_output(self, output: str):
        output_stripped = output.strip()
        output_lower = output_stripped.lower()

        if not output_stripped:
            return

        actual_errors = [
            "error:",
            "failed:",
            "failure:",
            "exception:",
            "panic:",
            "fatal:",
            "could not",
            "cannot",
            "unable to",
            "permission denied",
            "access denied",
            "not found",
            "invalid",
            "timeout",
            "connection refused",
            "network error",
            "authentication failed",
            "authorization failed",
            "resource not found",
            "conflict",
            "internal server error",
            "bad request",
            "forbidden",
        ]

        is_actual_error = any(error in output_lower for error in actual_errors)

        if is_actual_error:
            self.logger.error(output_stripped)
            for handler in self.logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.flush()

        if self.verbose or is_actual_error:
            self.console.print(output_stripped)

    def create_stack(self):
        try:
            self._stack = auto.create_stack(
                stack_name=self.stack_name, work_dir=self._infra_base_path
            )
        except auto.StackAlreadyExistsError:
            self.log_and_print(
                f"[yellow]Stack {self.stack_name} already exists. Selecting existing stack.[/yellow]",
                level="warning",
            )
            try:
                self._stack = auto.select_stack(
                    stack_name=self.stack_name, work_dir=self._infra_base_path
                )
            except Exception as e:
                self.log_and_print(
                    f"[red]Failed to select existing stack {self.stack_name}: {str(e)}[/red]",
                    level="error",
                    exc=e,
                )
                raise
        except Exception as e:
            self.log_and_print(
                f"[red]Failed to create stack {self.stack_name}: {str(e)}[/red]",
                level="error",
                exc=e,
            )
            raise
        return self._stack

    def deploy(self):
        self.log_and_print(
            f"[bold green]Deploying infrastructure for stack: {self.stack_name} using operation: {self.operation}[/bold green]"
        )

        try:
            stack = self.create_stack()
            self.log_and_print(f"[bold blue]Stack {self.stack_name} ready.[/bold blue]")

            result = stack.up(on_output=self._log_output)
            self.log_and_print(
                f"Update summary:\n{json.dumps(result.summary.resource_changes, indent=4)}"
            )
            self.log_and_print(
                f"[bold green]Deployment completed successfully for stack: {self.stack_name}[/bold green]"
            )
        except Exception as e:
            self.log_and_print(
                f"[red]Deployment failed for stack {self.stack_name}: {str(e)}[/red]",
                level="error",
                exc=e,
            )
            raise

    def destroy(self):
        self.log_and_print(
            f"[bold red]Destroying infrastructure for stack: {self.stack_name} using operation: {self.operation}[/bold red]"
        )

        try:
            stack = self.create_stack()
            self.log_and_print(f"[bold blue]Stack {self.stack_name} ready.[/bold blue]")

            result = stack.destroy(on_output=self._log_output)
            self.log_and_print(
                f"Destroy summary:\n{json.dumps(result.summary.resource_changes, indent=4)}"
            )
            self.log_and_print(
                f"[bold red]Destruction completed successfully for stack: {self.stack_name}[/bold red]"
            )
        except Exception as e:
            self.log_and_print(
                f"[red]Destruction failed for stack {self.stack_name}: {str(e)}[/red]",
                level="error",
                exc=e,
            )
            raise

    def refresh(self):
        self.log_and_print(
            f"[bold yellow]Refreshing infrastructure for stack: {self.stack_name} using operation: {self.operation}[/bold yellow]"
        )

        try:
            stack = self.create_stack()
            self.log_and_print(f"[bold blue]Stack {self.stack_name} ready.[/bold blue]")

            result = stack.refresh(on_output=self._log_output)
            self.log_and_print(
                f"Refresh summary:\n{json.dumps(result.summary.resource_changes, indent=4)}"
            )
            self.log_and_print(
                f"[bold yellow]Refresh completed successfully for stack: {self.stack_name}[/bold yellow]"
            )
        except Exception as e:
            self.log_and_print(
                f"[red]Refresh failed for stack {self.stack_name}: {str(e)}[/red]",
                level="error",
                exc=e,
            )
            raise

    def get_log_file_path(self) -> str:
        return self.log_file

    def _signal_handler(self, signum, frame):
        self.log_and_print(
            f"[yellow]Received signal {signum}. Cleaning up...[/yellow]",
            level="warning",
        )
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        try:
            if hasattr(self, "logger") and self.logger:
                self.logger.info("Cleaning up InfraDeployer resources")
                for handler in self.logger.handlers[:]:
                    if isinstance(handler, logging.FileHandler):
                        handler.flush()
                        handler.close()
                        self.logger.removeHandler(handler)
                self.logger.handlers.clear()
            if hasattr(self, "_stack") and self._stack:
                self._stack = None
        except Exception as e:
            self.log_and_print(
                f"[red]Cleanup error: {str(e)}[/red]", level="error", exc=e
            )

    def __del__(self):
        self.cleanup()
