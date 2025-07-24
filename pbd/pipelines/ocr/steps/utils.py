import shutil
import os
import zipfile

# Helper methods - defined inside class for better encapsulation
def download_pdf(client, key: str,
                  download_dir: str,
                  bucket_name:str) -> str:
    """Download a PDF file from MinIO to a local directory."""
    local_path = os.path.join(download_dir, os.path.basename(key))
    try:
        response = client.get_object(bucket_name, key)
        with open(local_path, "wb") as file_data:
            shutil.copyfileobj(response, file_data)
        # Verify the file was written successfully
        if os.path.getsize(local_path) == 0:
            raise Exception(f"Downloaded file {local_path} is empty")
        return local_path
    except Exception as e:
        print.error(f"Failed to download {key}: {str(e)}")
        raise


def zip_images(image_dir: str, output_zip_path: str):
    """Zip all images in a directory into a single zip file."""
    try:
            with zipfile.ZipFile(
                output_zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6
            ) as zipf:
                file_count = 0
                for root, _, files in os.walk(image_dir):
                    # Filter for image files
                    files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp'))]
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, image_dir)
                        zipf.write(file_path, arcname)
                        file_count += 1

                print(f"Zipped {file_count} files")

    except Exception as e:
            print(f"Error creating zip file: {str(e)}")
            raise
