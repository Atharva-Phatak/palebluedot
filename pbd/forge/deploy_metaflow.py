# deploy_pipeline.py

import sys
from metaflow import Deployer
from pathlib import Path

if __name__ == "__main__":
    pipeline_path = Path(sys.argv[1]).resolve()
    deployer = (
        Deployer(
            flow_file=str(pipeline_path),
            show_output=True,
        )
        .argo_workflows()
        .create()
    )
