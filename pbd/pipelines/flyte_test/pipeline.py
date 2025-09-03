# file: my_workflow.py
from flytekit import task, workflow, Resources


@task(
    container_image="ghcr.io/atharva-phatak/pbd-flyte_test:latest",
    requests=Resources(cpu="1", mem="512Mi"),
    limits=Resources(cpu="2", mem="1Gi"),
    environment={
        "AWS_ACCESS_KEY_ID": "minio@1234",
        "AWS_SECRET_ACCESS_KEY": "minio@local1234",
        "AWS_REGION": "us-east-1",
    },
)
def compute_square(x: int) -> int:
    return x * x


@workflow
def square_wf(x: int = 4) -> int:
    return compute_square(x=x)
