from pathlib import Path
from zipfile import ZipFile



def extract_zip(zip_path: str, extract_to: str) -> list[str]:
    """
    Extracts image files from a zip archive to a target directory.

    Args:
        zip_path (str): Path to the zip archive.
        extract_to (str): Directory to extract files into.

    Returns:
        list[str]: List of extracted image file paths (jpg, jpeg, png).
    """
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
