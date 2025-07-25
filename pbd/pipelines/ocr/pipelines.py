"""
PDF to Image Conversion Metaflow Pipeline for Kubernetes with JSON Configuration

This Metaflow pipeline processes PDFs from MinIO storage by:
- Discovering available PDFs
- Converting them to images in parallel
- Zipping the images
- Uploading results back to MinIO

All configuration is loaded from a JSON file, keeping the original K8s decorators intact.
"""

import os
from minio import Minio
from metaflow import FlowSpec, step, trigger, Parameter, kubernetes, environment
from pbd.helper.profilers.gpu import gpu_profile
from pbd.helper.logger import setup_logger
import json
import time
from pbd.helper.interface.pydantic_models import DataProcessingPipelineConfig
from pbd.helper.slack import send_slack_message
from pbd.pipelines.ocr.steps.utils import download_pdf
import pbd.pipelines.ocr.steps.query_mistral as query_mistral
from pbd.pipelines.ocr.steps.utils import zip_images
from pbd.helper.s3_paths import pdf_markdown_path, minio_zip_path
from pbd.pipelines.ocr.steps.marker_ocr import process_pdf_via_marker
from pbd.helper.s3_paths import data_processing_pipeline_config_path

logger = setup_logger(__name__)

# Docker image configuration
IMAGE_NAME = "ghcr.io/atharva-phatak/pbd-ocr:latest"


@trigger(event="minio.upload")
class PDFToMarkdownFlow(FlowSpec):
    """
    Metaflow pipeline for converting PDFs to images and uploading to MinIO reacting to argo events.
    """

    filename = Parameter("filename", help="The changed file name")
    bucket_name = Parameter(
        "bucket_name", help="The name of the MinIO bucket to process PDFs from"
    )
    config_uri = Parameter(
        "config_uri",
        help="URI to the JSON configuration file for the pipeline",
    )

    @kubernetes(
        image=IMAGE_NAME,
        cpu=1,
        memory=56,
        secrets=["aws-credentials", "slack-secret"],
    )
    @step
    def start(self):
        """
        Initialize the flow and validate environment using JSON configuration
        """
        print("Starting PDF to Image conversion pipeline...")

        self.access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        self.secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        self.slack_token = os.environ.get("SLACK_TOKEN")

        if not self.access_key or not self.secret_key:
            raise ValueError("AWS credentials not found in environment variables")

        print(f"Received filename: {self.filename} with bucket: {self.bucket_name}")
        client = Minio(
            endpoint="minio-palebluedot.io",
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=False,
        )
        try:
            config_path = data_processing_pipeline_config_path()
            response = client.get_object(self.bucket_name, config_path)
            config_bytes = response.read()
            config_data = json.loads(config_bytes.decode("utf-8"))
            pydantic_model_input = {
                "bucket_name": self.bucket_name,
                "filepath": self.filename,
                "output_path": config_data.get("output_path"),
                "slack_channel": config_data.get("slack_channel"),
                "image_dpi": config_data.get("image_dpi", 300),
                "endpoint": "http://minio-palebluedot.io",
            }
            self.config = DataProcessingPipelineConfig(**pydantic_model_input)
            print(f"Loaded configuration: {self.config}")
            print(f"Successfully loaded config from {config_path}")

        except Exception as e:
            logger.error(f"Failed to load config from MinIO: {e}")
            raise

        print(f"Processing PDFs from bucket: {self.config.bucket_name}")
        print(f"Input prefix: {self.config.filepath}")
        print(f"Output prefix: {self.config.output_path}")

        self.next(self.process_pdfs)

    @kubernetes(
        image=IMAGE_NAME,
        cpu=4,
        memory=10000,
        gpu=1,
        persistent_volume_claims={"mk-ocr-pvc": "/ocr_models"},
        shared_memory=2048,
        labels={"app": "ocr_pipeline", "component": "ocr"},
        secrets=["aws-credentials", "slack-secret"],
    )
    @environment(vars={"CUDA_VISIBLE_DEVICES": "0"})
    @gpu_profile(interval=90, include_artifacts=False)
    @step
    def process_pdfs(self):
        """
        Process individual PDFs in parallel with higher resource allocation
        """

        # Initialize MinIO client for this parallel branch
        client = Minio(
            endpoint=self.config.endpoint.replace("http://", "").replace(
                "https://", ""
            ),
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=False,
        )

        print(f"Available models : {os.listdir('/ocr_models')}")
        tmpdir = "tempdir"  # Define the path first
        os.makedirs(tmpdir, exist_ok=True)  # Create it
        print(f"Using temporary directory: {tmpdir}")

        # Check available disk space
        statvfs = os.statvfs(tmpdir)
        free_space_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)
        print(f"Available disk space: {free_space_gb:.2f} GB")

        # Download PDF
        pdf_path = download_pdf(
            client=client,
            key=self.filename,
            download_dir=tmpdir,
            bucket_name=self.config.bucket_name,
        )
        print(f"Downloaded {self.filename} to {pdf_path}")

        # Convert PDF to images using config settings
        # pages_count, image_output_dir = convert_pdf_to_images(pdf_path=pdf_path, tmpdir=tmpdir)
        # print(f"Converted {self.filename} to images in {image_output_dir}")

        # Create zip
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]

        start = time.time()

        markdown_path = os.path.join(tmpdir, f"{pdf_name}.md")
        # Store content to markdown file

        if self.config.use_mistral:
            print(f"Processing PDF {pdf_name} via Mistral...")
            images_dir = self._process_pdfs_via_mistral(
                pdf_path=pdf_path, markdown_path=markdown_path
            )
        else:
            print(f"Processing PDF {pdf_name} via Marker...")
            images_dir = self._process_pdfs_via_marker(
                tempdir=tmpdir, pdf_path=pdf_path, filename=pdf_name
            )

        # Upload markdown file to MinIO
        self._dump_md_to_minio(
            pdf_name=pdf_name,
            local_path=markdown_path,
            client=client,
        )
        if images_dir is not None:
            zip_output_path = minio_zip_path(pdf_name)
            zip_path = os.path.join(tmpdir, f"{pdf_name}.zip")
            zip_images(images_dir, zip_path)
            print(f"Created zip at {zip_path}")
            print(f"uploading zip file to MinIO at {zip_output_path}")
            # Upload to MinIO
            client.fput_object(
                bucket_name=self.config.bucket_name,
                object_name=zip_output_path,
                file_path=zip_path,
                content_type="application/zip",
            )
            print(f"Uploaded zip for {pdf_name} to MinIO at {zip_output_path}")
            print(
                f"Time taken to process {pdf_name}: {time.time() - start:.2f} seconds"
            )
            self.result = {
                "pdf_key": self.filename,
                "status": "success",
            }

        self.next(self.end)

    @kubernetes(
        image=IMAGE_NAME,
        cpu=1,
        memory=56,
        secrets=["aws-credentials", "slack-secret"],
    )
    @step
    def end(self):
        """
        End the flow
        """
        print("PDF to Image conversion pipeline completed!")
        print("Results: {}".format(self.result))
        send_slack_message(
            token=self.slack_token,
            message=f"✅ PDF to Image conversion completed for {self.config.filepath}!",
            channel="#metaflow-pipelines",
        )

    def _dump_md_to_minio(self, pdf_name: str, local_path: str, client: Minio):
        upload_path = pdf_markdown_path(pdf_name)
        try:
            client.fput_object(
                bucket_name=self.config.bucket_name,
                object_name=upload_path,
                file_path=local_path,
                content_type="text/markdown",
            )
            print(f"Uploaded markdown to MinIO at {upload_path}")
        except Exception as e:
            print(f"Failed to upload markdown to MinIO: {e}")
            raise ValueError(f"Failed to upload markdown to MinIO: {e}")

    def _process_pdfs_via_mistral(self, pdf_path: str, markdown_path: str) -> str:
        """Process PDF using Mistral OCR and save to markdown file."""
        markdown_images_dir = query_mistral.fetch_pdf_content(
            pdf_path=pdf_path, output_path=markdown_path
        )
        print(f"Markdown file created at {markdown_path}")
        return markdown_images_dir

    def _process_pdfs_via_marker(self, tempdir: str, pdf_path: str, filename: str):
        """Process PDF using Marker OCR and save output."""
        process_pdf_via_marker(pdf_path=pdf_path, output_dir=tempdir, filename=filename)
        # Images are stored in the same tempdir
        return tempdir


if __name__ == "__main__":
    PDFToMarkdownFlow()
