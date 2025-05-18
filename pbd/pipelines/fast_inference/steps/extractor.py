from zenml import step
from zipfile import ZipFile
from pathlib import Path
from typing import List

@step
def extract_zip(zip_path: str, extract_to: str) -> List[str]:
    zip_path = Path(zip_path)
    extract_to = Path(extract_to)
    extract_to.mkdir(parents=True, exist_ok=True)

    with ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

    image_files = [str(p) for p in extract_to.glob("*") if p.suffix.lower() in [".jpg", ".jpeg", ".png"]]
    return image_files
