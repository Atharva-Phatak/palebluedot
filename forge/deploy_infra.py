import typer
from rich.console import Console
from infrastructure.deploy import deploy_sequentially
import os
from dotenv import load_dotenv

app = typer.Typer()
console = Console()


# Load secrets
secret_path: str = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".secrets")
)
console.print(f"🔐 Loading secrets from: {secret_path}")
load_dotenv(os.path.join(secret_path, ".env"))


class InfraDeployer:
    def __init__(self, operation: str, group: str = "default"):
        self.operation = operation
        self.group = group
        self.passphrase = None
        if not self.passphrase:
            self.passphrase = "password"
            os.environ["PULUMI_CONFIG_PASSPHRASE"] = self.passphrase

    def deploy(self):
        console.print(f"✅ [green]Deploying group:[/green] {self.group}")

        if self.operation == "create" and self.group == "default":
            deploy_sequentially()
        else:
            raise ValueError(
                f"Unsupported operation '{self.operation}' for group '{self.group}'."
            )
