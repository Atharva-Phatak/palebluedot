"""
OCR Pipeline converted to Metaflow

This module provides a Metaflow pipeline for performing OCR on images using a multimodal LLM.
It includes steps for downloading, extracting, OCR processing, and post-processing text.
"""

import os
from metaflow import FlowSpec, step, kubernetes, environment, Config
from pbd.pipelines.ocr_engine.steps.prompt import ocr_prompt
from pbd.helper.logger import setup_logger
from pbd.pipelines.ocr_engine.steps.ocr import ocr_images
from pbd.pipelines.ocr_engine.steps.process_text import extract_problem_solution
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = setup_logger(__name__)


class OCRFlow(FlowSpec):
    """
    Metaflow pipeline for OCR processing of images from zip files
    """

    config = Config(
        "config",
        help="JSON configuration file for the pipeline",
        default="config.json",
    )

    @kubernetes(
        image=config.image,
        cpu=1,
        memory=56,
        secrets=["aws-credentials", "slack-secret"],
    )
    @step
    def start(self):
        """
        Initialize the pipeline
        """
        logger.info("Starting OCR pipeline")

        self.next(self.process_ocr)

    @kubernetes(
        image=config.image,
        cpu=4,
        memory=18000,
        gpu=1,
        persistent_volume_claims={"mk-model-pvc": "/models"},
        shared_memory=1024,
        labels={"app": "ocr_pipeline", "component": "process_ocr"},
        secrets=["aws-credentials", "slack-secret"],
    )
    @environment(vars={"CUDA_VISIBLE_DEVICES": "0"})
    @step
    def process_ocr(self):
        """
        Perform OCR inference on extracted images
        """
        self.run_test = self.config.run_test == "true"
        self.ocr_texts = ocr_images(
            endpoint=self.config.minio_endpoint,
            bucket=self.config.bucket,
            object_key=self.config.minio_object_key,
            local_path=self.config.local_path,
            model_path=self.config.ocr_model_path,
            extract_to=self.config.extract_to,
            max_new_tokens=self.ocr_config.max_new_tokens,
            batch_size=self.config.extraction_batch_size,
            prompt=ocr_prompt,
            run_test=self.run_test,
            filename=self.config.filename,
        )

        self.next(self.post_process)

    @kubernetes(
        image=config.image,
        cpu=4,
        memory=18000,
        gpu=1,
        persistent_volume_claims={"mk-model-pvc": "/models"},
        shared_memory=1024,
        labels={"app": "ocr_pipeline", "component": "post_process_ocr"},
        secrets=["aws-credentials", "slack-secret"],
    )
    @environment(vars={"CUDA_VISIBLE_DEVICES": "0"})
    @step
    def post_process(self):
        """
        Post-process OCR results to extract problem-solution pairs
        """
        logger.info("Starting post-processing step")

        extract_problem_solution(
            data=self.ocr_texts,
            model_path=self.config.post_processing_model_path,
            sampling_params=self.config.post_processing_params,
            batch_size=self.config.post_processing_batch_size,
            bucket_name=self.config.bucket,
            filename=self.config.filename,
            minio_endpoint=self.config.minio_endpoint,
        )

        self.next(self.end)

    @kubernetes(
        cpu=1,
        memory=56,
        secrets=["aws-credentials", "slack-secret"],
    )
    @step
    def end(self):
        """
        Final step of the pipeline
        """
        slack_token = os.environ.get("SLACK_TOKEN")
        logger.info("OCR pipeline completed successfully!")
        logger.info(f"Processed {len(self.ocr_results)} pages")
        logger.info(f"Results stored in MinIO bucket '{self.bucket}'")

        try:
            client = WebClient(token=slack_token)
            message = f"""
                    PDF Processing Pipeline Completed!
                    ✅ Successfully processed: {self.ocr_results} pages."""

            _ = client.chat_postMessage(
                channel=self.config.slack_channel, text=message.strip()
            )
            logger.info(f"Slack notification sent to {self.config.slack_channel}")
        except SlackApiError as e:
            logger.error(f"Error sending Slack message: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending Slack notification: {e}")


if __name__ == "__main__":
    OCRFlow()
