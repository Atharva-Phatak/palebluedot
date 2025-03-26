import requests
from bs4 import BeautifulSoup
from pbd.pipelines.data_collection.steps.validation import ExtractedData
from zenml import step
import minio
import os
from minio import Minio
import logging

ROOT_PATH = "/pbd"

@step(name="download_data",
      )
def download_books(books_to_download: list[ExtractedData],
                   bucket_name:str):
    minio_access_key = "minio@1234"
    minio_secret_key = "minio@local1234"
    minio_ingress_host = "fsml-minio.info"
    client = Minio(endpoint=minio_ingress_host,
                   access_key=minio_access_key,
                   secret_key=minio_secret_key, )
    logging.info(f"Downloading {len(books_to_download)} books")
    max_bytes = 50 * 1024
    for book in books_to_download:
        try:
            response = requests.get(book.links[0])
            if response.status_code != 200:
                logging.warning(f"Download failed for {book.links[0]}")
                continue

            soup = BeautifulSoup(response.content, "html.parser")
            download_link = soup.find("a", string="GET")["href"]
            download_link = "http://libgen.li/" + download_link
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Referer": "http://libgen.is/"
            }
            logging.info(f"Downloading {download_link}")
            response = requests.get(download_link, headers=headers, allow_redirects=True)
            if response.status_code == 200:
                downloaded_size = 0
                local_path = book.title + ".pdf"
                local_path = ROOT_PATH + "/" + local_path
                minio_path = "/raw_books/"+ local_path
                logging.info(f"Downloading {local_path}")
                with open(local_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=1024):
                        if downloaded_size + len(chunk) > max_bytes:
                            file.write(chunk[: max_bytes - downloaded_size])  # Only write remaining bytes
                            break
                        file.write(chunk)
                        downloaded_size += len(chunk)
                result = client.fput_object(bucket_name=bucket_name,
                               file_path = local_path,
                               object_name=minio_path)
                if result.version_id is not None:
                    logging.info(f"Successfully uploaded to minio at path {minio_path}")
                os.remove(local_path)
            else:
                logging.warning(f"Download failed for {download_link}")
        except Exception as e:
            logging.error(f"Failed to download {book.links}: {e}")
