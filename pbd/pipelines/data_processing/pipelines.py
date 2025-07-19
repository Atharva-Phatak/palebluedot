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
import tempfile
from minio import Minio
from metaflow import FlowSpec, step, trigger, Parameter
from pbd.helper.logger import setup_logger
from setting import processing_k8s, orchestrator_k8s
import json
from pbd.helper.interface.pydantic_models import DataProcessingPipelineConfig
from pbd.helper.slack import send_slack_message
from pbd.pipelines.data_processing.steps.utils import download_pdf, zip_images
from pbd.pipelines.data_processing.steps.pdf_to_image import convert_pdf_to_images, build_page_to_prompt
from pbd.helper.s3_paths import pdf_prompt_path
logger = setup_logger(__name__)


@trigger(event="minio.upload")
class PDFToImageFlow(FlowSpec):
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

    @orchestrator_k8s
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
            response = client.get_object(self.bucket_name, self.config_uri)
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
            print(f"Successfully loaded config from {self.config_uri}")

        except Exception as e:
            logger.error(f"Failed to load config from MinIO: {e}")
            raise

        print(f"Processing PDFs from bucket: {self.config.bucket_name}")
        print(f"Input prefix: {self.config.filepath}")
        print(f"Output prefix: {self.config.output_path}")

        self.next(self.process_pdfs)

    @processing_k8s
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

        with tempfile.TemporaryDirectory() as tmpdir:
                print(f"Using temporary directory: {tmpdir}")

                # Check available disk space
                statvfs = os.statvfs(tmpdir)
                free_space_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)
                print(f"Available disk space: {free_space_gb:.2f} GB")

                # Download PDF
                pdf_path = download_pdf(client=client,
                                        key=self.filename,
                                        download_dir=tmpdir,
                                        bucket_name=self.config.bucket_name)
                print(f"Downloaded {self.filename} to {pdf_path}")


                # Convert PDF to images using config settings
                pages_count, image_output_dir = convert_pdf_to_images(pdf_path=pdf_path, tmpdir=tmpdir)
                print(f"Converted {self.filename} to images in {image_output_dir}")

                # Create zip
                pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
                zip_path = os.path.join(tmpdir, f"{pdf_name}.zip")
                zip_images(image_output_dir, zip_path)
                print(f"Created zip at {zip_path}")

                # Build prompts for finetuning
                prompts = build_page_to_prompt(
                    pdf_path=pdf_path,
                    page_count = pages_count
                )
                print(f"Built prompts for {pdf_name}")
                # Dump prompts to MinIO
                self._dump_json_to_minio(
                    pdf_name=pdf_name,
                    tmpdir=tmpdir,
                    prompts=prompts,
                    client=client)
                print(f"Dumped prompts to MinIO at {pdf_prompt_path(pdf_name)}")


                print(f"uploading zip file to MinIO at {self.config.output_path}{pdf_name}.zip")
                # Upload to MinIO
                zip_key = f"{self.config.output_path}{pdf_name}.zip"
                client.fput_object(
                    bucket_name=self.config.bucket_name,
                    object_name=zip_key,
                    file_path=zip_path,
                    content_type="application/zip",
                )
                print(f"Uploaded zip for {pdf_name} to MinIO at {zip_key}")




                self.result = {
                    "pdf_key": self.filename,
                    "zip_key": zip_key,
                    "status": "success",
                    "pages_processed": pages_count,
                }


        self.next(self.end)

    @orchestrator_k8s
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
            channel="#zenml-pipelines",
        )

    def _dump_json_to_minio(self,
                            pdf_name:str,
                            tmpdir:str,
                            prompts:dict,
                            client: Minio):
        prompt_path = pdf_prompt_path(pdf_name)
        with open(os.path.join(tmpdir, f"{pdf_name}.json"), "w") as f:
            json.dump(prompts, f)
        client.fput_object(
            bucket_name=self.config.bucket_name,
            object_name=prompt_path,
            file_path=os.path.join(tmpdir, f"{pdf_name}.json"),
            content_type="application/json",
        )







if __name__ == "__main__":
    PDFToImageFlow()
