"""
Data Processing Steps for PDF to Image Conversion and Upload

This module provides steps and utility functions for:
- Downloading PDFs from MinIO
- Converting PDF pages to images
- Zipping images
- Uploading zipped images back to MinIO
- Parallel processing of multiple PDFs

Functions:
    download_pdf(s3_client, bucket, key, download_dir):
        Download a PDF file from MinIO to a local directory.

    zip_images(image_dir, output_zip_path):
        Zip all images in a directory into a single zip file.

    convert_and_upload(args):
        Convert a PDF to images, zip them, and upload the zip to MinIO.

    split_and_upload_pdfs(input_prefix, output_prefix, bucket_name, endpoint):
        ZenML step to process all PDFs in a MinIO bucket, convert to images, zip, and upload.

"""

from zenml import step
import os
from minio import Minio
from pbd.helper.logger import setup_logger
from multiprocessing import Pool, cpu_count
import tempfile
import shutil
import zipfile
import pymupdf
from zenml.client import Client

logger = setup_logger(__name__)


def download_pdf(s3_client, bucket: str, key: str, download_dir: str) -> str:
    """
    Download a PDF file from MinIO to a local directory.

    Args:
        s3_client (Minio): MinIO client instance.
        bucket (str): Name of the MinIO bucket.
        key (str): Object key (path) of the PDF in the bucket.
        download_dir (str): Local directory to save the PDF.

    Returns:
        str: Local file path to the downloaded PDF.
    """
    local_path = os.path.join(download_dir, os.path.basename(key))
    response = s3_client.get_object(bucket, key)
    with open(local_path, "wb") as file_data:
        shutil.copyfileobj(response, file_data)
    return local_path


def zip_images(image_dir: str, output_zip_path: str):
    """
    Zip all images in a directory into a single zip file.

    Args:
        image_dir (str): Directory containing image files to zip.
        output_zip_path (str): Output path for the created zip file.
    """
    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(image_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, image_dir)
                zipf.write(file_path, arcname)


def convert_and_upload(args):
    """
    Convert a PDF to images, zip them, and upload the zip to MinIO.

    Args:
        args (tuple): (key, bucket, endpoint, input_key_prefix, output_key_prefix)
            key (str): Object key of the PDF in MinIO.
            bucket (str): MinIO bucket name.
            endpoint (str): MinIO server endpoint.
            input_key_prefix (str): Prefix for input PDFs.
            output_key_prefix (str): Prefix for output zip files.

    Raises:
        ValueError: If AWS credentials are missing.
    """
    key, bucket, endpoint, input_key_prefix, output_key_prefix = args

    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not access_key or not secret_key:
        raise ValueError("AWS credentials not found in environment variables.")

    # Initialize MinIO client
    client = Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=False,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = download_pdf(client, bucket, key, tmpdir)
        logger.info(f"Downloaded {key} to {pdf_path}")
        pdf = pymupdf.open(pdf_path)
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        logger.info(f"Converted {pdf_name} to {len(pdf)} pages.")
        # Create a directory to store image files
        image_output_dir = os.path.join(tmpdir, pdf_name)
        os.makedirs(image_output_dir, exist_ok=True)

        for i in range(len(pdf)):
            page = pdf[i]
            page = page.get_pixmap(dpi=300)
            img_path = os.path.join(image_output_dir, f"page_{i + 1}.jpg")
            page.save(img_path, "JPEG")
        logger.info(f"Saved {len(pdf)} images for {pdf_name}.")
        # Create zip
        zip_path = os.path.join(tmpdir, f"{pdf_name}.zip")
        zip_images(image_output_dir, zip_path)
        logger.info(f"Created zip at {zip_path}")

        # Upload to MinIO
        zip_key = f"{output_key_prefix}{pdf_name}.zip"
        client.fput_object(
            bucket_name=bucket,
            object_name=zip_key,
            file_path=zip_path,
            content_type="application/zip",
        )
        logger.info(f"Uploaded zip for {pdf_name} to MinIO at {zip_key}")
        # Remove the zip file from local after uploading
        os.remove(zip_path)
        logger.info(f"Removed local zip file at {zip_path}")


@step(enable_step_logs=True, enable_cache=False)
def split_and_upload_pdfs(
    input_prefix: str, output_prefix: str, bucket_name: str, endpoint: str
):
    """
    ZenML step to process all PDFs in a MinIO bucket:
    - Downloads each PDF
    - Converts each page to an image
    - Zips the images
    - Uploads the zip file back to MinIO

    Args:
        input_prefix (str): Prefix for input PDFs in the bucket.
        output_prefix (str): Prefix for output zip files in the bucket.
        bucket_name (str): MinIO bucket name.
        endpoint (str): MinIO server endpoint.

    Raises:
        ValueError: If AWS credentials are missing.
    """
    access_key = os.environ.get("AWS_ACCESS_KEY_ID")
    secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
    if not access_key or not secret_key:
        raise ValueError("AWS credentials not found in environment variables.")

    client = Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=False,
    )

    pdf_objects = client.list_objects(bucket_name, prefix=input_prefix, recursive=True)
    pdfs = [obj.object_name for obj in pdf_objects if obj.object_name.endswith(".pdf")]
    zips = [obj.object_name for obj in pdf_objects if obj.object_name.endswith(".zip")]
    zip_prefixes = [zip[:-4] for zip in zips if zip.endswith(".zip")]

    pdfs_to_process = [
        pdf
        for pdf in pdfs
        if not any(pdf.startswith(prefix) for prefix in zip_prefixes)
    ]

    logger.info(f"PDFs found: {pdfs_to_process}")

    # Prepare argument tuples for multiprocessing
    args_list = [
        (pdf_key, bucket_name, endpoint, input_prefix, output_prefix)
        for pdf_key in pdfs_to_process
    ]

    with Pool(processes=(cpu_count() // 2)) as pool:
        pool.map(convert_and_upload, args_list)
    Client().active_stack.alerter.post("Step finished!")
