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
from metaflow import FlowSpec, step, trigger, Parameter
from pbd.helper.logger import setup_logger
from setting import processing_k8s, orchestrator_k8s
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import json
from pbd.helper.interface.pydantic_models import DataProcessingPipelineConfig

logger = setup_logger(__name__)


@trigger(event="minio.upload")
class PDFToImageFlow(FlowSpec):
    """
    Metaflow pipeline for converting PDFs to images and uploading to MinIO
    All configuration loaded from JSON file, maintaining original K8s decorators
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
        logger.info("Starting PDF to Image conversion pipeline...")

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
            response = client.get_object(self.bucket_name, self.config_uri)
            config_bytes = response.read()
            config_data = json.loads(config_bytes.decode("utf-8"))
            pydantic_model_input = {
                "bucket_name": config_data.get("bucket_name"),
                "filepath": self.filename,
                "output_path": config_data.get("output_path"),
                "slack_channel": config_data.get("slack_channel"),
                "image_dpi": config_data.get("image_dpi", 300),
                "endpoint": "http://minio-palebluedot.io",
            }
            self.config = DataProcessingPipelineConfig(**pydantic_model_input)
            logger.info(f"Loaded configuration: {self.config}")
            logger.info(f"Successfully loaded config from {self.config_uri}")

        except Exception as e:
            logger.error(f"Failed to load config from MinIO: {e}")
            raise

        logger.info(f"Processing PDFs from bucket: {self.config.bucket_name}")
        logger.info(f"Input prefix: {self.config.filepath}")
        logger.info(f"Output prefix: {self.config.output_path}")

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

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                logger.info(f"Using temporary directory: {tmpdir}")

                # Check available disk space
                statvfs = os.statvfs(tmpdir)
                free_space_gb = (statvfs.f_frsize * statvfs.f_bavail) / (1024**3)
                logger.info(f"Available disk space: {free_space_gb:.2f} GB")

                # Download PDF
                pdf_path = self._download_pdf(client, self.filename, tmpdir)
                logger.info(f"Downloaded {self.filename} to {pdf_path}")

                # Check PDF file size
                pdf_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
                logger.info(f"PDF size: {pdf_size_mb:.2f} MB")

                # Convert PDF to images using config settings
                image_output_dir = self._convert_pdf_to_images(pdf_path, tmpdir)
                logger.info(
                    f"Converted {self.filename} to images in {image_output_dir}"
                )

                # Create zip
                pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
                zip_path = os.path.join(tmpdir, f"{pdf_name}.zip")
                self._zip_images(image_output_dir, zip_path)
                logger.info(f"Created zip at {zip_path}")

                # Check zip file size
                zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
                logger.info(f"Zip size: {zip_size_mb:.2f} MB")

                # Upload to MinIO
                zip_key = f"{self.config.output_path}{pdf_name}.zip"
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
                    "pdf_size_mb": pdf_size_mb,
                    "zip_size_mb": zip_size_mb,
                }

        except Exception as e:
            logger.error(f"Error processing {self.pdf_key}: {str(e)}", exc_info=True)
            self.result = {"pdf_key": self.pdf_key, "status": "failed", "error": str(e)}

        self.next(self.end)

    @orchestrator_k8s
    @step
    def end(self):
        """
        End the flow
        """
        logger.info("PDF to Image conversion pipeline completed!")
        logger.info("Results: {}".format(self.result))
        if self.slack_token is not None:
            self._send_slack_notification(filename=self.filename)

    # Helper methods - defined inside class for better encapsulation
    def _download_pdf(self, client, key: str, download_dir: str) -> str:
        """Download a PDF file from MinIO to a local directory."""
        local_path = os.path.join(download_dir, os.path.basename(key))
        try:
            response = client.get_object(self.config.bucket_name, key)
            with open(local_path, "wb") as file_data:
                shutil.copyfileobj(response, file_data)
            # Verify the file was written successfully
            if os.path.getsize(local_path) == 0:
                raise Exception(f"Downloaded file {local_path} is empty")
            return local_path
        except Exception as e:
            logger.error(f"Failed to download {key}: {str(e)}")
            raise

    def _convert_pdf_to_images(self, pdf_path: str, tmpdir: str) -> str:
        """Convert PDF pages to images using configuration settings."""
        pdf_doc = None
        try:
            # Open PDF with error checking
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            pdf_doc = pymupdf.open(pdf_path)
            if pdf_doc.is_closed:
                raise Exception("PDF document is closed after opening")

            pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
            self.pages_count = len(pdf_doc)
            logger.info(f"Converting {pdf_name} with {self.pages_count} pages.")

            if self.pages_count == 0:
                raise Exception("PDF contains no pages")

            # Create a directory to store image files
            image_output_dir = os.path.join(tmpdir, pdf_name)
            os.makedirs(image_output_dir, exist_ok=True)

            image_format = "png"
            dpi = 300

            for i in range(self.pages_count):
                try:
                    page = pdf_doc[i]
                    # Use a reasonable DPI to avoid memory issues
                    pixmap = page.get_pixmap(dpi=dpi)
                    extension = (
                        "jpg"
                        if image_format.upper() == "JPEG"
                        else image_format.lower()
                    )
                    img_path = os.path.join(
                        image_output_dir, f"page_{i + 1}.{extension}"
                    )
                    pixmap.save(img_path, image_format)

                    # Clear pixmap to free memory
                    pixmap = None

                    if i % 10 == 0:  # Log progress every 10 pages
                        logger.info(f"Processed page {i + 1}/{self.pages_count}")

                except Exception as e:
                    logger.error(f"Error processing page {i + 1}: {str(e)}")
                    raise

            logger.info(
                f"Saved {self.pages_count} images for {pdf_name} at {dpi} DPI in {image_format} format."
            )
            return image_output_dir

        except Exception as e:
            logger.error(f"Error converting PDF to images: {str(e)}")
            raise
        finally:
            # Ensure PDF is properly closed
            if pdf_doc and not pdf_doc.is_closed:
                pdf_doc.close()

    def _zip_images(self, image_dir: str, output_zip_path: str):
        """Zip all images in a directory into a single zip file."""
        try:
            with zipfile.ZipFile(
                output_zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6
            ) as zipf:
                file_count = 0
                for root, _, files in os.walk(image_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, image_dir)
                        zipf.write(file_path, arcname)
                        file_count += 1

                logger.info(f"Zipped {file_count} files")

        except Exception as e:
            logger.error(f"Error creating zip file: {str(e)}")
            raise

    def _send_slack_notification(self, filename: str):
        """Send a Slack message with the results of the flow."""
        slack_token = os.environ.get("SLACK_TOKEN")
        try:
            client = WebClient(token=slack_token)

            message = f"""
                PDF Processing Pipeline Completed!
                ✅ Successfully processed: {filename}
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
