import os
import pulumi.automation as auto
from rich.console import Console
import json
from dotenv import load_dotenv

secret_path: str = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", ".secrets")
)
load_dotenv(os.path.join(secret_path, ".env"))
console = Console()


class InfraDeployer:
    def __init__(self, stack_name: str, operation: str, passphrase: str = None):
        self.stack_name = stack_name
        self.operation = operation
        self.passphrase = passphrase
        self._infra_base_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "infra")
        )

        # Set passphrase if provided
        if not self.passphrase:
            self.passphrase = "password"
            os.environ["PULUMI_CONFIG_PASSPHRASE"] = self.passphrase
        elif not os.environ.get("PULUMI_CONFIG_PASSPHRASE") and not os.environ.get(
            "PULUMI_CONFIG_PASSPHRASE_FILE"
        ):
            console.print(
                "[red]Error: No passphrase found. Please set PULUMI_CONFIG_PASSPHRASE environment variable or provide passphrase parameter.[/red]"
            )
            raise ValueError("Pulumi passphrase is required but not provided")

        if not os.path.exists(self._infra_base_path):
            console.print(
                f"[red]Error: Infrastructure base path {self._infra_base_path} does not exist.[/red]"
            )
            raise FileNotFoundError(
                f"Infrastructure base path {self._infra_base_path} does not exist."
            )
        console.print(
            f"[bold blue]InfraDeployer initialized with stack: {self.stack_name}, operation: {self.operation}[/bold blue] at {self._infra_base_path}"
        )

    def create_stack(self):
        try:
            stack = auto.create_stack(
                stack_name=self.stack_name,
                work_dir=self._infra_base_path,
            )
        except auto.StackAlreadyExistsError:
            console.print(
                f"[yellow]Stack {self.stack_name} already exists. Selecting existing stack.[/yellow]"
            )
            stack = auto.select_stack(
                stack_name=self.stack_name,
                work_dir=self._infra_base_path,
            )
        return stack

    def deploy(self):
        console.print(
            f"[bold green]Deploying infrastructure for stack: {self.stack_name} using operation: {self.operation}[/bold green]"
        )
        stack = self.create_stack()
        console.print(
            f"[bold blue]Stack {self.stack_name} created/selected.[/bold blue]"
        )
        up_results = stack.up(
            on_output=console.print,
        )
        console.print(
            f"update summary: \n{json.dumps(up_results.summary.resource_changes, indent=4)}"
        )

    def destroy(self):
        console.print(
            f"[bold red]Destroying infrastructure for stack: {self.stack_name} using operation: {self.operation}[/bold red]"
        )
        stack = self.create_stack()
        console.print(
            f"[bold blue]Stack {self.stack_name} created/selected.[/bold blue]"
        )
        destroy_results = stack.destroy(
            auto.DestroyOptions(
                on_output=console.print,
                message=f"Destroying stack {self.stack_name} with operation {self.operation}",
            )
        )
        console.print(
            f"destroy summary: \n{json.dumps(destroy_results.summary.resource_changes, indent=4)}"
        )

    def refresh(self):
        console.print(
            f"[bold yellow]Refreshing infrastructure for stack: {self.stack_name} using operation: {self.operation}[/bold yellow]"
        )
        stack = self.create_stack()
        console.print(
            f"[bold blue]Stack {self.stack_name} created/selected.[/bold blue]"
        )
        refresh_results = stack.refresh(
            on_output=console.print,
        )
        console.print(
            f"refresh summary: \n{json.dumps(refresh_results.summary.resource_changes, indent=4)}"
        )


# Usage example:
if __name__ == "__main__":
    # Option 1: Pass passphrase directly
    deployer = InfraDeployer("my-stack", "deploy", passphrase="your-secure-passphrase")

    # Option 2: Use environment variable (set before running)
    # deployer = InfraDeployer("my-stack", "deploy")

    deployer.deploy()
