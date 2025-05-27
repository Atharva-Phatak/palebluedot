from zenml import pipeline
from pbd.pipelines.data_processing.steps.data_process import split_and_upload_pdfs
from pbd.pipelines.data_processing.setting import docker_settings, k8s_operator_settings


@pipeline(
    name="process_pdfs_for_extraction",
    settings={
        "docker": docker_settings,
        "orchestrator": k8s_operator_settings,
    },
)
def process_pdfs(
    input_prefix: str,
    output_prefix: str,
    bucket_name: str = "data-bucket",
    endpoint: str = "fsml-minio.info",
):
    split_and_upload_pdfs(
        input_prefix=input_prefix,
        output_prefix=output_prefix,
        bucket_name=bucket_name,
        endpoint=endpoint,
    )


if __name__ == "__main__":
    process_pdfs(
        input_prefix="raw_data/input_pdfs/",
        output_prefix="processed_data/pdfs/",
        bucket_name="data-bucket",
        endpoint="fsml-minio.info",
    )
