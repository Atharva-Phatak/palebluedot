#!/usr/bin/env python3
"""
PaleBlueDot GitHub Pipeline Trigger - Typer CLI
Repository: https://github.com/Atharva-Phatak/palebluedot
"""

import os
import requests
from typing import Optional, Dict, Any
import typer
from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv

# Get the absolute path of the current file
current_file = os.path.abspath(__file__)

# Go up two levels: from pbd/helper → pbd → PaleBlueDot
project_root = os.path.abspath(os.path.join(current_file, "..", "..", ".."))

# Construct path to .env inside the .secrets folder
env_path = os.path.join(project_root, ".secrets", ".env")
load_dotenv(env_path)
app = typer.Typer(help="GitHub Workflow Trigger for PaleBlueDot")
console = Console()


class GitHubWorkflowTrigger:
    """GitHub Workflow Trigger Class"""

    def __init__(self, owner: str = "Atharva-Phatak", repo: str = "palebluedot"):
        self.owner = owner
        self.repo = repo
        self.api_base = f"https://api.github.com/repos/{owner}/{repo}"
        self.token = self._get_token()
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.token}",
            "Content-Type": "application/json",
        }

    def _get_token(self) -> str:
        """Get GitHub token from environment"""
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            console.print("[red]❌ GITHUB_TOKEN not found in environment[/red]")
            raise typer.Exit(1)
        return token

    def _check_workflow_exists(self, workflow_name: str) -> bool:
        """Check if workflow exists"""
        try:
            response = requests.get(
                f"{self.api_base}/actions/workflows/{workflow_name}",
                headers=self.headers,
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def trigger_workflow(
        self,
        workflow_name: str,
        branch: str = "main",
        inputs: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Trigger a GitHub Actions workflow"""
        # Check if workflow exists
        if not self._check_workflow_exists(workflow_name):
            console.print(f"[red]❌ Workflow '{workflow_name}' not found[/red]")
            return False

        # Prepare payload
        payload = {"ref": branch}
        if inputs:
            payload["inputs"] = inputs

        # Make API call
        try:
            response = requests.post(
                f"{self.api_base}/actions/workflows/{workflow_name}/dispatches",
                headers=self.headers,
                json=payload,
            )

            if response.status_code == 204:
                console.print(
                    f"[green]✅ Triggered '{workflow_name}' on '{branch}'[/green]"
                )
                return True
            else:
                console.print(
                    f"[red]❌ Failed to trigger workflow (HTTP {response.status_code})[/red]"
                )
                return False

        except requests.exceptions.RequestException as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            return False

    def list_workflows(self) -> None:
        """List available workflows"""
        try:
            response = requests.get(
                f"{self.api_base}/actions/workflows", headers=self.headers
            )

            if response.status_code == 200:
                workflows = response.json().get("workflows", [])

                table = Table(title="Available Workflows")
                table.add_column("Name", style="cyan")
                table.add_column("Path", style="magenta")
                table.add_column("State", style="green")

                for workflow in workflows:
                    table.add_row(
                        workflow.get("name", "N/A"),
                        workflow.get("path", "N/A"),
                        workflow.get("state", "N/A"),
                    )

                console.print(table)
            else:
                console.print(
                    f"[red]❌ Failed to fetch workflows (HTTP {response.status_code})[/red]"
                )

        except requests.exceptions.RequestException as e:
            console.print(f"[red]❌ Error: {e}[/red]")
