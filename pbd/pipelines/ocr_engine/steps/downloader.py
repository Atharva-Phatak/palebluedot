from minio import Minio
from pathlib import Path
from zipfile import ZipFile
import os


def download_from_minio(
    endpoint: str,
    bucket: str,
    object_key: str,
    local_path: str,
) -> str:
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

    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    client.fget_object(bucket, object_key, str(local_path))

    return str(local_path)


def extract_zip(zip_path: str, extract_to: str) -> list[str]:
    zip_path = Path(zip_path)
    extract_to = Path(extract_to)
    extract_to.mkdir(parents=True, exist_ok=True)

    with ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)

    image_files = [
        str(p)
        for p in extract_to.glob("*")
        if p.suffix.lower() in [".jpg", ".jpeg", ".png"]
    ]
    return image_files
