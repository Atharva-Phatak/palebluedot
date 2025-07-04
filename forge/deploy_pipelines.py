import typing as T
from pathlib import Path
from rich.console import Console
import os
import subprocess

console = Console()


class PipelineDeployer:
    def __init__(self, profile: T.Optional[str] = None, env: T.Optional[dict] = None):
        self.profile = profile
        self.env = env or {}
        self.pipelines_base_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "pbd/pipelines")
        )
        self.pipelines_base_path = Path(self.pipelines_base_path)

    def discover_pipelines(self) -> list[str]:
        """Discover available pipelines in the pbd/pipelines directory"""
        if not self.pipelines_base_path.exists():
            console.print(
                f"[red]Error: Pipeline directory {self.pipelines_base_path} not found[/red]"
            )
            return []

        pipelines = []
        for item in self.pipelines_base_path.iterdir():
            if item.is_dir():
                pipeline_file = item / "pipelines.py"
                if pipeline_file.exists():
                    pipelines.append(item.name)

        return pipelines

    def get_pipeline_path(self, pipeline_name: str) -> T.Optional[Path]:
        """Get the full path to a pipeline file"""
        pipeline_path = self.pipelines_base_path / pipeline_name / "pipelines.py"

        if not pipeline_path.exists():
            console.print(
                f"[red]Error: Pipeline file not found at {pipeline_path}[/red]"
            )
            return None

        return pipeline_path

    def deploy_to_argo(self, pipeline_name: str, **deploy_kwargs) -> bool:
        pipeline_path = self.get_pipeline_path(pipeline_name)
        console.print(f"[blue]Deploying pipeline: {pipeline_path}[/blue]")
        if not pipeline_path:
            return False
        venv_python = pipeline_path.parent / ".venv" / "bin" / "python"
        deploy_script = Path(__file__).parent / "deploy_metaflow.py"
        pale_blue_dot_dir = deploy_script.parent.parent  # PaleBlueDot
        console.print(f"[blue]Using virtual environment Python: {venv_python}[/blue]")
        console.print(f"[blue]Using deployment script: {deploy_script}[/blue]")
        console.print(f"[blue]Using PaleBlueDot directory: {pale_blue_dot_dir}[/blue]")
        if not venv_python.exists():
            console.print(
                f"[red]Error: Virtual environment Python not found at {venv_python}[/red]"
            )
            return False
        if not deploy_script.exists():
            console.print(
                f"[red]Error: Deployment script not found at {deploy_script}[/red]"
            )
            return False
        try:
            # Set up environment with PYTHONPATH
            env = os.environ.copy()
            env["PYTHONPATH"] = str(pale_blue_dot_dir)

            subprocess.run(
                [str(venv_python), str(deploy_script), str(pipeline_path)],
                check=True,
                cwd=str(pale_blue_dot_dir),
                env=env,  # Pass the modified environment
            )
            return True
        except subprocess.CalledProcessError as e:
            console.print(
                f"[red]❌ Deployment failed with exit code {e.returncode}[/red]"
            )
        return False
