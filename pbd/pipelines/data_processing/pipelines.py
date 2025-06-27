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
import shutil
import zipfile
import pymupdf
from minio import Minio
from metaflow import FlowSpec, step, Config
from pbd.helper.logger import setup_logger
from setting import discovery_k8s, processing_k8s, lightweight_k8s, orchestrator_k8s
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = setup_logger(__name__)


class PDFToImageFlow(FlowSpec):
    """
    Metaflow pipeline for converting PDFs to images and uploading to MinIO
    All configuration loaded from JSON file, maintaining original K8s decorators
    """

    # JSON Configuration - only configuration needed
    config = Config(
        "config",
        help="JSON configuration file for the pipeline",
        default="pdf_processing_config.json",
    )

    @orchestrator_k8s
    @step
    def start(self):
        """
        Initialize the flow and validate environment using JSON configuration
        """
        logger.info("Starting PDF to Image conversion pipeline...")

        self.access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        self.secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        self.slack_token = os.environ.get("SLACK_TOKEN")
        if not self.access_key or not self.secret_key:
            raise ValueError("AWS credentials not found in environment variables")

        logger.info(f"Processing PDFs from bucket: {self.config.bucket_name}")
        logger.info(f"Input prefix: {self.config.input_prefix}")
        logger.info(f"Output prefix: {self.config.output_prefix}")

        self.next(self.discover_pdfs)

    @discovery_k8s
    @step
    def discover_pdfs(self):
        """
        Discover PDFs to process and filter out already processed ones
        """
        # Initialize MinIO client
        client = Minio(
            endpoint=self.config.endpoint.replace("http://", "").replace(
                "https://", ""
            ),
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=False,
        )

        # Get list of PDFs and existing zips
        pdf_objects = client.list_objects(
            self.config.bucket_name, prefix=self.config.input_prefix, recursive=True
        )
        zip_objects = client.list_objects(
            self.config.bucket_name, prefix=self.config.output_prefix, recursive=True
        )

        pdfs = [
            obj.object_name for obj in pdf_objects if obj.object_name.endswith(".pdf")
        ]
        zips = [
            obj.object_name for obj in zip_objects if obj.object_name.endswith(".zip")
        ]
        zip_prefixes = [zip.split("/")[-1][:-4] for zip in zips if zip.endswith(".zip")]

        # Filter out already processed PDFs
        self.pdfs_to_process = [
            pdf for pdf in pdfs if not any(prefix in pdf for prefix in zip_prefixes)
        ]

        logger.info(f"Found {len(pdfs)} total PDFs")
        logger.info(f"Found {len(zips)} existing zip files")
        logger.info(f"PDFs to process: {len(self.pdfs_to_process)}")

        if not self.pdfs_to_process:
            logger.info("No PDFs to process. All PDFs have already been converted.")
            self.next(self.end)
        else:
            self.next(self.process_pdfs, foreach="pdfs_to_process")

    @processing_k8s
    @step
    def process_pdfs(self):
        """
        Process individual PDFs in parallel with higher resource allocation
        """
        self.pdf_key = self.input

        # Initialize MinIO client for this parallel branch
        client = Minio(
            endpoint=self.config.endpoint.replace("http://", "").replace(
                "https://", ""
            ),
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=False,
        )

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # Download PDF
                pdf_path = self._download_pdf(client, self.pdf_key, tmpdir)
                logger.info(f"Downloaded {self.pdf_key} to {pdf_path}")

                # Convert PDF to images using config settings
                image_output_dir = self._convert_pdf_to_images(pdf_path, tmpdir)

                # Create zip
                pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
                zip_path = os.path.join(tmpdir, f"{pdf_name}.zip")
                self._zip_images(image_output_dir, zip_path)
                logger.info(f"Created zip at {zip_path}")

                # Upload to MinIO
                zip_key = f"{self.config.output_prefix}{pdf_name}.zip"
                client.fput_object(
                    bucket_name=self.config.bucket_name,
                    object_name=zip_key,
                    file_path=zip_path,
                    content_type="application/zip",
                )
                logger.info(f"Uploaded zip for {pdf_name} to MinIO at {zip_key}")

                self.result = {
                    "pdf_key": self.pdf_key,
                    "zip_key": zip_key,
                    "status": "success",
                    "pages_processed": self.pages_count,
                }

        except Exception as e:
            logger.error(f"Error processing {self.pdf_key}: {str(e)}")
            self.result = {"pdf_key": self.pdf_key, "status": "failed", "error": str(e)}

        self.next(self.join_results)

    @lightweight_k8s
    @step
    def join_results(self, inputs):
        """
        Collect results from all parallel processing branches
        """
        self.results = []
        successful = 0
        failed = 0

        for inp in inputs:
            self.results.append(inp.result)
            if inp.result["status"] == "success":
                successful += 1
            else:
                failed += 1

        logger.info("\nProcessing Summary:")
        logger.info(f"Successfully processed: {successful} PDFs")
        logger.info(f"Failed: {failed} PDFs")

        if failed > 0:
            logger.info("\nFailed PDFs:")
            for result in self.results:
                if result["status"] == "failed":
                    logger.info(f"  - {result['pdf_key']}: {result['error']}")

        # Send Slack notification if configured
        if hasattr(self.config, "slack") and hasattr(self.config.slack, "token_env"):
            self._send_slack_notification(successful, failed)

        self.next(self.end)

    @orchestrator_k8s
    @step
    def end(self):
        """
        End the flow
        """
        logger.info("PDF to Image conversion pipeline completed!")
        if hasattr(self, "results"):
            total_pages = sum(
                r.get("pages_processed", 0)
                for r in self.results
                if r["status"] == "success"
            )
            logger.info(f"Total pages processed: {total_pages}")

    # Helper methods - defined inside class for better encapsulation
    def _download_pdf(self, client, key: str, download_dir: str) -> str:
        """Download a PDF file from MinIO to a local directory."""
        local_path = os.path.join(download_dir, os.path.basename(key))
        response = client.get_object(self.config.bucket_name, key)
        with open(local_path, "wb") as file_data:
            shutil.copyfileobj(response, file_data)
        return local_path

    def _convert_pdf_to_images(self, pdf_path: str, tmpdir: str) -> str:
        """Convert PDF pages to images using configuration settings."""
        pdf = pymupdf.open(pdf_path)
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        self.pages_count = len(pdf)
        logger.info(f"Converting {pdf_name} with {self.pages_count} pages.")

        # Get DPI and format from config - direct access
        dpi = self.config.pdf_processing.dpi
        image_format = self.config.pdf_processing.image_format

        # Create a directory to store image files
        image_output_dir = os.path.join(tmpdir, pdf_name)
        os.makedirs(image_output_dir, exist_ok=True)

        for i in range(len(pdf)):
            page = pdf[i]
            pixmap = page.get_pixmap(dpi=dpi)
            extension = (
                "jpg" if image_format.upper() == "JPEG" else image_format.lower()
            )
            img_path = os.path.join(image_output_dir, f"page_{i + 1}.{extension}")
            pixmap.save(img_path, image_format)

        pdf.close()
        logger.info(
            f"Saved {len(pdf)} images for {pdf_name} at {dpi} DPI in {image_format} format."
        )
        return image_output_dir

    def _zip_images(self, image_dir: str, output_zip_path: str):
        """Zip all images in a directory into a single zip file."""
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(image_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, image_dir)
                    zipf.write(file_path, arcname)

    def _send_slack_notification(self, successful: int, failed: int):
        """Send a Slack message with the results of the flow."""
        try:
            client = WebClient(token=self.config.slack_token)

            message = f"""
                PDF Processing Pipeline Completed!
                ✅ Successfully processed: {successful} PDFs
                ❌ Failed: {failed} PDFs
                📊 Total pages processed: {sum(r.get("pages_processed", 0) for r in self.results if r["status"] == "success")}
            """

            _ = client.chat_postMessage(
                channel=self.config.slack_channel, text=message.strip()
            )
            logger.info(f"Slack notification sent to {self.config.slack_channel}")

        except SlackApiError as e:
            logger.error(f"Error sending Slack message: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending Slack notification: {e}")


if __name__ == "__main__":
    PDFToImageFlow()
