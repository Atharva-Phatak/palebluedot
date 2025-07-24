from mistralai import Mistral
import os
import datauri
def upload_pdf(filepath:str,
               client:Mistral):
    """Uploads a PDF file to Mistral and returns a signed URL for processing."""
    filename = filepath.split("/")[-1]
    uploaded_pdf = client.files.upload(
    file={
      "file_name": filename,
      "content": open(filepath, "rb"),
    },
    purpose="ocr"
    )
    signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)
    return signed_url.url

def get_mistral_client() -> Mistral:
    """Initializes and returns a Mistral client using the MISTRAL_TOKEN environment variable."""
    mistral_token = os.environ.get("MISTRAL_TOKEN")
    if not mistral_token:
        raise ValueError("MISTRAL_TOKEN environment variable is not set.")
    return Mistral(
        api_key = mistral_token,
    )


def save_image(image):
    """Saves an image from the OCR response to a file."""
    parsed = datauri.parse(image.image_base64)
    with open(image.id, "wb") as file:
      file.write(parsed.data)

def create_markdown_file(response, output_path: str):
    """Creates a markdown file from the OCR response, including images and text. Saves images in a sub"""
    output_dir = os.path.dirname(output_path)
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    with open(output_path, "wt") as f:
        for page in response.pages:
            page_md = page.markdown
            for image in page.images:
                image_path = os.path.join("images", f"{image.id}.png")
                full_path = os.path.join(images_dir, f"{image.id}.png")

                # Save image
                parsed = datauri.parse(image.image_base64)
                with open(full_path, "wb") as img_file:
                    img_file.write(parsed.data)

                # Replace image id reference in markdown
                page_md = page_md.replace(f"![image]({image.id})", f"![image]({image_path})")

            f.write(page_md + "\n\n")

    print(f"Markdown file created at {output_path} with {len(response.pages)} pages.")
    return images_dir


def fetch_pdf_content(pdf_path:str,output_path:str):
    """
    Fetches the content of a PDF file using Mistral API.
    """
    client = get_mistral_client()
    signed_url = upload_pdf(pdf_path, client)
    response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": signed_url,
            },
            include_image_base64=True,
            )
    if "detail" in response:
       print(f"Error processing PDF: {response['detail']}")
    else:
        print(f"PDF processed successfully. Storing content to {output_path}")
        images_path = create_markdown_file(response, output_path)
        return images_path
