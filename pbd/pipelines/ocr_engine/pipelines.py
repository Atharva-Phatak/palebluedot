"""
ocr_pipeline.py

This module defines the OCRFlow Metaflow pipeline for performing Optical Character Recognition (OCR) on images using a multimodal Large Language Model (LLM). The pipeline is designed to automate the process of extracting text from images, post-processing the extracted text, and notifying users upon completion.

Pipeline Steps:
---------------
1. **start**: Initializes the pipeline and logs the start of the OCR process.
2. **process_ocr**: Performs OCR inference on images extracted from a zip file using a specified model and configuration.
3. **post_process**: Post-processes the OCR results to extract problem-solution pairs using a post-processing model.
4. **end**: Finalizes the pipeline, logs completion, and sends a notification to a Slack channel.

Configuration:
--------------
- The pipeline uses a JSON configuration file to specify parameters such as model paths, batch sizes, MinIO endpoints, and Slack channel information.
- Kubernetes resources and secrets are configured for each step to ensure secure and efficient execution.

Dependencies:
-------------
- Metaflow: For pipeline orchestration.
- pbd.pipelines.ocr_engine.steps: Contains the OCR and post-processing logic.
- slack_sdk: For sending notifications to Slack.
- pbd.helper.logger: For logging.

Usage:
------
To run the pipeline, execute this module as the main program. Ensure that all dependencies are installed and the configuration file is properly set up.

Example:
--------
    python ocr_pipeline.py

Notes:
------
- This pipeline is intended for use in environments with access to Kubernetes and the required secrets for AWS and Slack.
- Ensure that the MinIO and model paths are accessible from the execution environment.
- For detailed documentation on each step, refer to the respective modules in `pbd.pipelines.ocr_engine.steps`.

OCR Pipeline converted to Metaflow

This module provides a Metaflow pipeline for performing OCR on images using a multimodal LLM.
It includes steps for downloading, extracting, OCR processing, and post-processing text.
"""

import os

from metaflow import (
    FlowSpec,
    environment,
    kubernetes,
    step,
    trigger_on_finish,
    current,
)
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from pbd.helper.s3_paths import ocr_engine_config_path
from pbd.pipelines.ocr_engine.steps.ocr import ocr_images
from minio import Minio
import json
from pbd.helper.interface.pydantic_models import OCRPipelineConfig
from pbd.helper.s3_paths import minio_zip_path
from pbd.helper.profilers.gpu import gpu_profile

IMAGE_NAME = "ghcr.io/atharva-phatak/pbd-ocr_engine:latest"


@trigger_on_finish(flow="PDFToImageFlow")
class OCRFlow(FlowSpec):
    """
    Metaflow pipeline for OCR processing of images from zip files
    """

    def _read_config(self, bucket_name: str, config_uri: str) -> OCRPipelineConfig:
        print("Starting OCR pipeline")
        self.access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        self.secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        self.slack_token = os.environ.get("SLACK_TOKEN")
        if not self.access_key or not self.secret_key:
            raise ValueError("AWS credentials not found in environment variables")
        client = Minio(
            endpoint="minio-palebluedot.io",
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=False,
        )
        try:
            response = client.get_object(bucket_name, config_uri)
            config_bytes = response.read()
            config_data = json.loads(config_bytes.decode("utf-8"))
            if "bucket" not in config_data:
                config_data["bucket"] = bucket_name
            if "filename" not in config_data:
                filename = current.trigger.run.data.filename.split("/")[-1].split(
                    ".pdf"
                )[0]
                config_data["filename"] = filename
                print(f"Filename not found in config, using: {filename}")
            if "extracted_zip_path" not in config_data:
                config_data["extracted_zip_path"] = minio_zip_path(
                    filename=config_data["filename"]
                )
            return OCRPipelineConfig(**config_data)
        except Exception as e:
            raise ValueError(f"Failed to read configuration from MinIO: {e}")

    @kubernetes(
        image=IMAGE_NAME,
        cpu=1,
        memory=56,
        secrets=["aws-credentials", "slack-secret", "argilla-auth-secret"],
    )
    @step
    def start(self):
        """
        Initialize the pipeline
        """

        self.bucket_name: str = current.trigger.run.data.bucket_name
        self.config = self._read_config(
            bucket_name=self.bucket_name,
            config_uri=ocr_engine_config_path(),
        )
        print(
            f"Received filename: {self.config.filename} with bucket: {self.bucket_name}"
        )

        self.next(self.process_ocr)

    @kubernetes(
        image=IMAGE_NAME,
        cpu=4,
        memory=10000,
        gpu=1,
        persistent_volume_claims={"mk-model-pvc": "/models"},
        shared_memory=2048,
        labels={"app": "ocr_pipeline", "component": "process_ocr"},
        secrets=["aws-credentials", "slack-secret", "argilla-auth-secret"],
    )
    @environment(vars={"CUDA_VISIBLE_DEVICES": "0"})
    @gpu_profile(interval=60, include_artifacts=False)
    @step
    def process_ocr(self):
        """
        Perform OCR inference on extracted images
        """
        _ = ocr_images(
            endpoint=self.config.minio_endpoint,
            bucket=self.config.bucket,
            minio_zip_path=self.config.extracted_zip_path,
            local_path=self.config.local_path,
            model_path=self.config.ocr_model_path,
            extract_to=self.config.extract_to,
            max_new_tokens=self.config.ocr_params.max_tokens,
            batch_size=self.config.ocr_model_batch_size,
            run_test=self.config.run_test,
            filename=self.config.filename,
        )
        print(f"OCR processing completed for {self.config.filename}")
        self.next(self.end)

    @kubernetes(
        image=IMAGE_NAME,
        cpu=1,
        memory=56,
        secrets=["aws-credentials", "slack-secret", "argilla-auth-secret"],
    )
    @step
    def end(self):
        """
        Final step of the pipeline
        """
        slack_token = os.environ.get("SLACK_TOKEN")
        print("OCR pipeline completed successfully!")
        print(f"Results stored in MinIO bucket '{self.config.bucket}'")

        try:
            client = WebClient(token=slack_token)
            message = f"""
                    PDF Processing Pipeline Completed for {self.config.filename}!"""

            _ = client.chat_postMessage(
                channel="#zenml-pipelines", text=message.strip()
            )
            print("Slack notification sent to #zenml-pipelines")
        except SlackApiError as e:
            print(f"Error sending Slack message: {e}")
        except Exception as e:
            print(f"Unexpected error sending Slack notification: {e}")


if __name__ == "__main__":
    OCRFlow()
