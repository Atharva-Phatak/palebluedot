"""
Data Processing Pipeline for PDF Extraction

This module defines the ZenML pipeline for processing PDFs:
- Converts PDFs to images
- Zips the images
- Uploads the zipped images to MinIO

Functions:
    process_pdfs(input_prefix, output_prefix, bucket_name, endpoint):
        ZenML pipeline to process and upload PDFs as zipped images.
"""

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
    """
    ZenML pipeline to process PDFs:
    - Converts each PDF in the MinIO bucket to images
    - Zips the images
    - Uploads the zipped images back to MinIO

    Args:
        input_prefix (str): Prefix for input PDFs in the bucket.
        output_prefix (str): Prefix for output zip files in the bucket.
        bucket_name (str, optional): MinIO bucket name. Defaults to "data-bucket".
        endpoint (str, optional): MinIO server endpoint. Defaults to "fsml-minio.info".
    """
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
        endpoint="palebluedot-minio.io",
    )
