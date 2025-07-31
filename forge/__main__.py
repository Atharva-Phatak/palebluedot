#!/usr/bin/env python3
"""
forge CLI
⚡ The ultimate tool for forging Metaflow pipelines into Argo Workflows
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from forge.deploy_pipelines import PipelineDeployer
from forge.deploy_infra import InfraDeployer
from forge.trigger_gh_actions import GitHubWorkflowTrigger
from forge.dependency import DependencyUpdater
from forge.create_template import create_pipeline

app = typer.Typer(
    name="forge",
    help="⚡ Forge - CLI to deploy infrastructure and pipelines",
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
            f"[bold magenta]⚡ Forge: Deploying Metaflow Pipeline: {pipeline_name}[/bold magenta]",
            border_style="magenta",
        )
    )

    pipeline_path = pipeline_deployer.get_pipeline_path(pipeline_name)
    if not pipeline_path:
        raise typer.Exit(1)

    success = pipeline_deployer.deploy_to_argo(pipeline_name)
    if not success:
        raise typer.Exit(1)

    console.print(f"[green]✅ Successfully forged pipeline: {pipeline_name}[/green]")
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
    console.print(
        Panel.fit(
            "[bold cyan]📋 forge: Listing Available Pipelines[/bold cyan]",
            border_style="cyan",
        )
    )

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
    group_name: str = typer.Argument(..., help="Name of the infrastructure stack"),
    operation: str = typer.Argument(
        ..., help="Operation to perform (create/destroy/refresh)"
    ),
):
    """⚙️ Deploy or manage infrastructure stacks"""
    console.print(
        Panel.fit(
            f"[bold blue]⚙️ forge: Performing '{operation}' on group: {group_name}[/bold blue]",
            border_style="blue",
        )
    )

    deployer = InfraDeployer(group=group_name, operation=operation)

    match operation:
        case "create":
            deployer.deploy()
        case "destroy":
            deployer.destroy()
        case "refresh":
            deployer.refresh()
        case _:
            console.print(
                "[red]Invalid operation. Use create, destroy, or refresh.[/red]"
            )
            raise typer.Exit(1)


@app.command()
def gh_build(
    branch: str = typer.Option("main", "--branch", "-b", help="Branch to run on"),
    pipeline_type: str = typer.Option(
        "metaflow", "--type", "-t", help="Type of pipeline to build (metaflow/webhook)"
    ),
    folder: Optional[str] = typer.Option(
        None,
        "--folder",
        "-f",
        help="Specific folder to build (overrides change detection)",
    ),
):
    """🚀 Trigger Metaflow/Webhook CI/CD workflow"""
    trigger = GitHubWorkflowTrigger()

    console.print(
        Panel.fit(
            f"[bold green]🚀 forge: Triggering GitHub Actions Workflow for type '{pipeline_type}' on branch '{branch}'[/bold green]",
            border_style="green",
        )
    )

    workflow_inputs = {"folder": folder} if folder else None

    if pipeline_type == "metaflow":
        success = trigger.trigger_workflow(
            "ci_cd_metaflow_pipelines.yaml", branch, workflow_inputs
        )
    elif pipeline_type == "webhook":
        success = trigger.trigger_workflow(
            "ci_cd_webhook.yaml", branch, workflow_inputs
        )
    else:
        console.print("[red]Invalid pipeline type. Use 'metaflow' or 'webhook'.[/red]")
        raise typer.Exit(1)

    if not success:
        raise typer.Exit(1)

    console.print("[green]✅ Workflow triggered successfully![/green]")


@app.command()
def list_gh_workflows():
    """🔍 List available GitHub Actions workflows"""
    console.print(
        Panel.fit(
            "[bold yellow]🔍 forge: Listing GitHub Actions Workflows[/bold yellow]",
            border_style="yellow",
        )
    )
    trigger = GitHubWorkflowTrigger()
    trigger.list_workflows()


@app.command()
def dependency_update(
    pipeline_name: str = typer.Argument(
        ..., help="Name of the pipeline folder in pbd/pipelines/"
    ),
    dependency: str = typer.Argument(
        ..., help='Dependency to install like "metaflow==2.15.18"'
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
):
    """🔧 Update a specific dependency in a pipeline"""
    console.print(
        Panel.fit(
            f"[bold white]🔧 forge: Updating Dependency in Pipeline: {pipeline_name}[/bold white]",
            border_style="white",
        )
    )

    updater = DependencyUpdater(
        pipeline_name=pipeline_name, dependency=dependency, verbose=verbose
    )
    updater.update_dependency()


@app.command()
def scaffold(
    pipeline_name: str = typer.Argument(..., help="Name of the pipeline to scaffold"),
):
    """🛠️ Scaffold a new pipeline template"""

    console.print(
        Panel.fit(
            f"[bold green]🛠️ forge: Scaffolding Pipeline Template: {pipeline_name}[/bold green]",
            border_style="green",
        )
    )

    try:
        create_pipeline(pipeline_name)
        console.print(
            f"[green]✅ Successfully created pipeline template: {pipeline_name}[/green]"
        )
    except Exception as e:
        console.print(f"[red]Error creating pipeline template: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
