import requests
from bs4 import BeautifulSoup
from urllib.request import urlretrieve
from pbd.steps.data_collection.validation import ExtractedData
from zenml import step
import minio
from zenml.logger import get_logger
import os

logger = get_logger(__name__)

@step(name="download_data",
      )
def download_books(books_to_download: list[ExtractedData],
                   client: minio.Minio,
                   bucket_name:str):
    for book in books_to_download:
        try:
            response = requests.get(book.link)
            if response.status_code != 200:
                logger.warning(f"Download failed for {book.link}")
                continue

            soup = BeautifulSoup(response.content, "html.parser")
            download_link = soup.find("a", string="GET")["href"]
            local_path = book.title + ".pdf"
            minio_path = "/raw_books/"+ local_path
            urlretrieve(download_link, local_path)
            result = client.fput_object(bucket_name=bucket_name,
                               file_path = local_path,
                               object_name=minio_path)
            if result.version_id is not None:
                logger.info(f"Successfully uploaded to minio at path {minio_path}")
            os.remove(local_path)
        except Exception as e:
            logger.error(f"Failed to download {book.link}: {e}")
