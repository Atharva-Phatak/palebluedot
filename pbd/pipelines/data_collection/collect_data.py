from pbd.pipelines.data_collection.steps.page_search import extract_pdf_links
from pbd.pipelines.data_collection.steps.download import download_books
from zenml import pipeline
from minio import Minio

@pipeline(name = "data_collection_pipeline",
          )
def data_collection_pipeline():
    pdf_links = extract_pdf_links(book_name="The Grand Design, Stephen Hawking")
    download_books(books_to_download=pdf_links,
                   bucket_name="data-bucket")

if __name__ == "__main__":
    data_collection_pipeline()