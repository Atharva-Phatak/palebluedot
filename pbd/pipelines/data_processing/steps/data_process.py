from zenml import step
import os
from minio import Minio
from pdf2image import convert_from_path
from pbd.helper.logger import setup_logger
from multiprocessing import Pool, cpu_count
import tempfile
import shutil
import zipfile

logger = setup_logger(__name__)


def download_pdf(s3_client, bucket: str, key: str, download_dir: str) -> str:
    local_path = os.path.join(download_dir, os.path.basename(key))
    response = s3_client.get_object(bucket, key)
    with open(local_path, "wb") as file_data:
        shutil.copyfileobj(response, file_data)
    return local_path


def zip_images(image_dir: str, output_zip_path: str):
    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(image_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, image_dir)
                zipf.write(file_path, arcname)


def convert_and_upload(args):
    key, bucket, endpoint, base_key_prefix = args

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
        pages = convert_from_path(pdf_path, dpi=300)
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]

        image_output_dir = os.path.join(tmpdir, pdf_name)
        for i, page in enumerate(pages):
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_img:
                page.save(tmp_img.name, "JPEG")

        # Create zip
        zip_path = os.path.join(tmpdir, f"{pdf_name}.zip")
        zip_images(image_output_dir, zip_path)

        # Upload to MinIO
        zip_key = f"{base_key_prefix}{pdf_name}.zip"
        client.fput_object(
            bucket_name=bucket,
            object_name=zip_key,
            file_path=zip_path,
            content_type="application/zip",
        )
        logger.info(f"Uploaded zip for {pdf_name} to MinIO at {zip_key}")


@step()
def split_and_upload_pdfs(input_prefix: str, bucket_name: str, endpoint: str):
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
    logger.info(f"PDFs found: {pdfs}")

    # Prepare argument tuples for multiprocessing
    args_list = [(pdf_key, bucket_name, endpoint, input_prefix) for pdf_key in pdfs]

    with Pool(processes=(cpu_count() // 2)) as pool:
        pool.map(convert_and_upload, args_list)
