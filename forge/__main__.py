#!/usr/bin/env python3
"""
FlowForge CLI
⚡ The ultimate tool for forging Metaflow pipelines into Argo Workflows
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from forge.deploy_pipelines import PipelineDeployer
from forge.deploy_infra import InfraDeployer

app = typer.Typer(
    name="forge",
    help="⚡ Forge - Forge a cli to deploy infrastructure and pipelines",
    rich_markup_mode="rich",
)

console = Console()


@app.command()
def deploy_pipeline(
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
    pipeline_deployer = PipelineDeployer()
    console.print(
        Panel.fit(
            f"[bold magenta]⚡ FlowForge: Forging Pipeline: {pipeline_name}[/bold magenta]",
            border_style="magenta",
        )
    )

    pipeline_path = pipeline_deployer.get_pipeline_path(pipeline_name)

    if not pipeline_path:
        raise typer.Exit(1)

    success = pipeline_deployer.deploy_to_argo(pipeline_name)
    if not success:
        raise typer.Exit(1)
    else:
        console.print(
            f"[green]✅ Successfully forged pipeline: {pipeline_name}[/green]"
        )
        console.print(f"[blue]Pipeline path: {pipeline_path}[/blue]")
        if profile:
            console.print(f"[blue]Using Metaflow profile: {profile}[/blue]")
        if namespace:
            console.print(f"[blue]Using Kubernetes namespace: {namespace}[/blue]")
        if image:
            console.print(f"[blue]Using Docker image: {image}[/blue]")


@app.command()
def list_pipelines():
    """📋 List all available pipelines"""
    pipeline_deployer = PipelineDeployer()
    pipelines = pipeline_deployer.discover_pipelines()

    if not pipelines:
        console.print("[yellow]No pipelines found in pbd/pipelines/[/yellow]")
        return

    table = Table(title="Available Pipelines")
    table.add_column("Pipeline Name", style="cyan")
    table.add_column("Path", style="dim")

    for pipeline in pipelines:
        pipeline_path = pipeline_deployer.pipelines_base_path / pipeline / "pipeline.py"
        table.add_row(pipeline, str(pipeline_path))

    console.print(table)


@app.command()
def infra_action(
    stack_name: str = typer.Argument(..., help="Name of the infrastructure stack"),
    operation: str = typer.Argument(
        ..., help="Operation to perform (create/destroy/refresh)"
    ),
):
    """⚙️ Deploy or manage infrastructure stacks"""

    console.print(
        Panel.fit(
            f"[bold blue]⚙️ FlowForge: Managing Infrastructure Stack: {stack_name}[/bold blue]",
            border_style="blue",
        )
    )

    deployer = InfraDeployer(stack_name=stack_name, operation=operation)

    if operation == "create":
        deployer.deploy()
    elif operation == "destroy":
        deployer.destroy()
    elif operation == "refresh":
        deployer.refresh()
    else:
        console.print("[red]Invalid operation. Use create, destroy, or refresh.[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
