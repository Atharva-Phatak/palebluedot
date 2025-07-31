import os
import subprocess


def create_pipeline(folder_name: str):
    template_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "copier_pipeline_template")
    )
    pipeline_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "pbd/pipelines", folder_name)
    )
    subprocess.run(
        [
            "copier",
            "copy",
            str(template_path),
            str(pipeline_path),  # 👈 Correct destination
            "-d",
            f"folder_name={folder_name}",
            "-d",
            f"destination_path=pbd/pipelines/{folder_name}",  # 👈 Jinja context, not actual FS path
        ]
    )
