"""
`pipelines.py`

This file defines the `OCRPostProcessFlow` class, which implements a Metaflow pipeline for post-processing OCR results.
The pipeline consists of multiple steps to read configuration, load data, process OCR results, and finalize the flow.

Classes:
---------
- `OCRPostProcessFlow`:
  A Metaflow pipeline class that orchestrates the post-processing of OCR results.

Functions:
----------
- `_read_config(bucket_name: str, config_uri: str) -> OCRPostProcessPipelineConfig`:
  Reads the pipeline configuration from MinIO storage and returns a validated configuration object.

- `_load_data()`:
  Loads OCR results from MinIO storage and returns the data as a list.

Steps:
------
- `start`:
  Initializes the pipeline by reading configuration and preparing for post-processing.

- `post_process`:
  Processes OCR results to extract problem-solution pairs using the specified model and parameters.

- `end`:
  Finalizes the pipeline and sends a Slack notification upon successful completion.

Constants:
----------
- `IMAGE_NAME`:
  Specifies the Docker image used for Kubernetes steps.

Dependencies:
-------------
- `metaflow`: Used for defining and managing the pipeline.
- `minio`: Used for interacting with MinIO storage.
- `datasets`: Used for loading OCR results in Parquet format.
- `pbd.helper`: Contains helper functions and models for the pipeline.
- `time`: Used for measuring execution time.
"""

from metaflow import (
    FlowSpec,
    environment,
    kubernetes,
    step,
    trigger_on_finish,
    current,
)
from pbd.helper.profilers.gpu import gpu_profile
import os
from minio import Minio
import json
from pbd.helper.interface.pydantic_models import OCRPostProcessPipelineConfig
from pbd.helper.s3_paths import ocr_results_path, ocr_post_process_config_path
from pbd.helper.file_download import download_from_minio
from datasets import load_dataset
from pbd.pipelines.ocr_post_process.steps.process_text import extract_problem_solution
import time
from pbd.helper.slack import send_slack_message

IMAGE_NAME = "ghcr.io/atharva-phatak/pbd-ocr_post_process:latest"


@trigger_on_finish(flow="PDFToMarkdownFlow")
class OCRPostProcessFlow(FlowSpec):
    """
    Metaflow pipeline for post-processing OCR results.
    """

    def _read_config(
        self, bucket_name: str, config_uri: str
    ) -> OCRPostProcessPipelineConfig:
        print("Starting Post-Processing Pipeline")
        self.access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        self.secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
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
                config_data["filename"] = current.trigger.run.data.config.filename
            return OCRPostProcessPipelineConfig(**config_data)
        except Exception as e:
            raise ValueError(f"Failed to read configuration from MinIO: {e}")

    def _load_data(self):
        ocr_results = ocr_results_path(
            filename=self.config.filename,
        )
        local_path = download_from_minio(
            endpoint=self.config.minio_endpoint,
            bucket=self.config.bucket,
            object_key=ocr_results,
            local_path=f"/tmp/{self.config.filename}.parquet",
        )
        ds = load_dataset("parquet", data_files=[local_path])
        return ds["train"]["content"].to_list()

    @kubernetes(
        image=IMAGE_NAME,
        cpu=1,
        memory=56,
        secrets=["aws-credentials", "slack-secret", "argilla-auth-secret"],
    )
    @step
    def start(self):
        """
        Start step to initialize the flow.
        """
        print("Starting OCR Post-Processing Pipeline")
        self.slack_token = os.environ.get("SLACK_TOKEN")
        self.bucket_name: str = current.trigger.run.data.bucket_name
        config_uri: str = ocr_post_process_config_path()
        self.config = self._read_config(
            bucket_name=self.bucket_name,
            config_uri=config_uri,
        )
        self.filename = self.config.filename
        self.next(self.post_process)

    @kubernetes(
        image=IMAGE_NAME,
        cpu=4,
        memory=16000,
        gpu=1,
        persistent_volume_claims={"mk-model-pvc": "/models"},
        shared_memory=2048,
        labels={"app": "ocr_pipeline", "component": "post_process_ocr"},
        secrets=["aws-credentials", "slack-secret"],
    )
    @environment(vars={"CUDA_VISIBLE_DEVICES": "0"})
    @gpu_profile(interval=60, include_artifacts=False)
    @step
    def post_process(self):
        """
        Post-process OCR results to extract problem-solution pairs
        """
        print("Starting post-processing step")
        start = time.time()
        data = self._load_data()
        print(f"Loaded {len(data)} records for post-processing from MinIO")
        extract_problem_solution(
            data=data,
            max_model_len=self.config.max_model_len,
            model_path=self.config.post_processing_model_path,
            sampling_params=self.config.post_processing_params.model_dump(
                exclude_none=True
            ),
            batch_size=self.config.post_processing_batch_size,
            bucket_name=self.config.bucket,
            filename=self.config.filename,
            minio_endpoint=self.config.minio_endpoint,
        )
        print(
            f"Post-processing completed for {self.config.filename} in {time.time() - start:.2f} seconds"
        )
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
        Final step to conclude the flow.
        """
        print("OCR Post-Processing Pipeline completed successfully.")
        send_slack_message(
            token=self.slack_token,
            message=f"✅ OCR Post-Processing pipeline completed successfully for {self.config.filename}!",
            channel="#zenml-pipelines",
        )


if __name__ == "__main__":
    OCRPostProcessFlow()
