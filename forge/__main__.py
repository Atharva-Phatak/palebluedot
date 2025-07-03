#!/usr/bin/env python3
"""
FlowForge CLI
⚡ The ultimate tool for forging Metaflow pipelines into Argo Workflows
"""

import typer
import sys
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from metaflow import Deployer

app = typer.Typer(
    name="forge",
    help="⚡ Forge - Forge Metaflow pipelines into Argo Workflows with style",
    rich_markup_mode="rich",
)

console = Console()


class PipelineDeployer:
    def __init__(self, profile: Optional[str] = None, env: Optional[dict] = None):
        self.profile = profile
        self.env = env or {}
        self.pipelines_base_path = Path("pbd/pipelines")

    def discover_pipelines(self) -> List[str]:
        """Discover available pipelines in the pbd/pipelines directory"""
        if not self.pipelines_base_path.exists():
            console.print(
                f"[red]Error: Pipeline directory {self.pipelines_base_path} not found[/red]"
            )
            return []

        pipelines = []
        for item in self.pipelines_base_path.iterdir():
            if item.is_dir():
                pipeline_file = item / "pipeline.py"
                if pipeline_file.exists():
                    pipelines.append(item.name)

        return pipelines

    def get_pipeline_path(self, pipeline_name: str) -> Optional[Path]:
        """Get the full path to a pipeline file"""
        pipeline_path = self.pipelines_base_path / pipeline_name / "pipeline.py"

        if not pipeline_path.exists():
            console.print(
                f"[red]Error: Pipeline file not found at {pipeline_path}[/red]"
            )
            return None

        return pipeline_path

    def deploy_to_argo(self, pipeline_name: str, **deploy_kwargs) -> bool:
        """Deploy pipeline to Argo Workflows using Metaflow's native deployer"""
        pipeline_path = self.get_pipeline_path(pipeline_name)
        if not pipeline_path:
            return False

        try:
            # Use Metaflow's native Argo Workflows deployer
            deployer = Deployer(
                flow_file=str(pipeline_path),
                profile=self.profile,
                env=self.env,
                show_output=True,
            )

            # Deploy to Argo Workflows
            deployed_flow = deployer.argo_workflows().create(**deploy_kwargs)

            console.print(
                f"[green]✅ Successfully forged {pipeline_name} into Argo Workflows[/green]"
            )

            # Show production token if available
            token = deployed_flow.production_token
            if token:
                console.print(f"[dim]Production token: {token}[/dim]")

            return True

        except Exception as e:
            console.print(f"[red]❌ Forging failed: {e}[/red]")
            return False


deployer = PipelineDeployer()


@app.command()
def deploy(
    pipeline_name: str = typer.Argument(..., help="Name of the pipeline to deploy"),
    profile: Optional[str] = typer.Option(
        None, "--profile", "-p", help="Metaflow profile to use for deployment"
    ),
    namespace: Optional[str] = typer.Option(
        None, "--namespace", "-n", help="Kubernetes namespace for deployment"
    ),
    image: Optional[str] = typer.Option(
        None, "--image", "-i", help="Docker image to use for the workflow"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force forging without confirmation"
    ),
):
    """⚡ Forge a Metaflow pipeline into Argo Workflows"""

    console.print(
        Panel.fit(
            f"[bold magenta]⚡ FlowForge: Forging Pipeline: {pipeline_name}[/bold magenta]",
            border_style="magenta",
        )
    )

    # Prepare deployment kwargs
    deploy_kwargs = {}
    if namespace:
        deploy_kwargs["namespace"] = namespace
    if image:
        deploy_kwargs["image"] = image

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # Validate pipeline exists
        task = progress.add_task("Validating pipeline...", total=None)
        pipeline_path = deployer.get_pipeline_path(pipeline_name)

        if not pipeline_path:
            raise typer.Exit(1)

        # Show confirmation unless force is used
        if not force:
            console.print(
                f"\n[yellow]About to forge pipeline '{pipeline_name}' into Argo Workflows[/yellow]"
            )
            console.print(f"[dim]Pipeline: {pipeline_path}[/dim]")
            if profile:
                console.print(f"[dim]Profile: {profile}[/dim]")
            if namespace:
                console.print(f"[dim]Namespace: {namespace}[/dim]")
            if image:
                console.print(f"[dim]Image: {image}[/dim]")

            if not Confirm.ask("Ready to forge?"):
                console.print("[yellow]Forging cancelled[/yellow]")
                raise typer.Exit(0)

        progress.update(task, description="Forging into Argo...")

        # Update deployer with profile
        deployer.profile = profile

        success = deployer.deploy_to_argo(pipeline_name, **deploy_kwargs)

        if not success:
            raise typer.Exit(1)


@app.command()
def list_pipelines():
    """📋 List all available pipelines"""
    pipelines = deployer.discover_pipelines()

    if not pipelines:
        console.print("[yellow]No pipelines found in pbd/pipelines/[/yellow]")
        return

    table = Table(title="Available Pipelines")
    table.add_column("Pipeline Name", style="cyan")
    table.add_column("Path", style="dim")

    for pipeline in pipelines:
        pipeline_path = deployer.pipelines_base_path / pipeline / "pipeline.py"
        table.add_row(pipeline, str(pipeline_path))

    console.print(table)


@app.command()
def config():
    """⚙️ Show current configuration"""

    table = Table(title="FlowForge Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Pipelines Path", str(deployer.pipelines_base_path))
    table.add_row("Current Profile", deployer.profile or "default")
    table.add_row("Metaflow Available", "✅" if "metaflow" in sys.modules else "❌")

    console.print(table)


if __name__ == "__main__":
    app()
