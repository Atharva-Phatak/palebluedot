import subprocess
import os
from pathlib import Path
import typer

app = typer.Typer()


class DependencyUpdater:
    def __init__(self, pipeline_name: str, dependency: str, verbose: bool = False):
        self.pipelines_base_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "pbd/pipelines")
        )
        self.pipelines_base_path = Path(self.pipelines_base_path)
        self.pipeline_path = Path(self.pipelines_base_path) / pipeline_name
        self.dependency = dependency
        self.verbose = verbose

        self.venv_path = Path(self.pipeline_path) / ".venv"
        self.python_bin = Path(self.venv_path) / "bin" / "python"

    def log(self, message: str):
        if self.verbose:
            typer.echo(f"[DependencyUpdater] {message}")

    def check_paths(self):
        if not self.pipeline_path.exists():
            raise FileNotFoundError(f"Pipeline folder not found: {self.pipeline_path}")
        if not self.venv_path.exists():
            raise FileNotFoundError(f"Virtualenv not found: {self.venv_path}")
        if not self.python_bin.exists():
            raise FileNotFoundError(
                f"Python binary not found in venv: {self.python_bin}"
            )

    def run_cmd(self, cmd: list[str]):
        self.log(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, cwd=self.pipeline_path, check=True)

    def update_dependency(self):
        self.check_paths()

        # Step 1: Add the dependency via uv
        self.run_cmd(["uv", "add", self.dependency, "--active"])

        # Step 2: Lock dependencies
        self.run_cmd(["uv", "lock"])

        # Step 3: Export requirements.txt
        with open(self.pipeline_path / "requirements.txt", "w") as f:
            subprocess.run(
                [
                    "uv",
                    "export",
                    "--no-hashes",
                    "--format",
                    "requirements-txt",
                ],
                cwd=self.pipeline_path,
                stdout=f,
                check=True,
            )
        self.log("Dependency update complete ✅")


if __name__ == "__main__":
    app()
