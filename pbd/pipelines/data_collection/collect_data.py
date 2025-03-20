from pbd.steps.data_collection.page_search import extract_pdf_links
from pbd.steps.data_collection.download import download_books
from zenml import pipeline
from minio import Minio

@pipeline(name = "data_collection_pipeline",
          enable_step_logs=True)
def data_collection_pipeline():
    minio_access_key = "minio@1234"
    minio_secret_key = "minio@local1234"
    minio_ingress_host = "http://fsml-minio.info"
    client = Minio(endpoint=minio_ingress_host,
                   access_key=minio_access_key,
                   secret_key=minio_secret_key,)
    pdf_links = extract_pdf_links()
