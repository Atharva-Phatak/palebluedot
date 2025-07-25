from surya.detection import DetectionPredictor
from surya.layout import LayoutPredictor
from surya.ocr_error import OCRErrorPredictor
from surya.recognition import RecognitionPredictor
from surya.table_rec import TableRecPredictor
from marker.converters.pdf import PdfConverter
from marker.output import save_output
import os

BASE_MODEL_DIR = "ocr_models"


def load_marker_models_dict(device=None, dtype=None):
    """Load the marker OCR models from the specified base directory."""
    return {
        "layout_model": LayoutPredictor(
            device=device, dtype=dtype, checkpoint=f"{BASE_MODEL_DIR}/layout/2025_02_18"
        ),
        "recognition_model": RecognitionPredictor(
            device=device,
            dtype=dtype,
            checkpoint=f"{BASE_MODEL_DIR}/text_recognition/2025_05_16",
        ),
        "table_rec_model": TableRecPredictor(
            device=device,
            dtype=dtype,
            checkpoint=f"{BASE_MODEL_DIR}/table_recognition/2025_02_18",
        ),
        "detection_model": DetectionPredictor(
            device=device,
            dtype=dtype,
            checkpoint=f"{BASE_MODEL_DIR}/text_detection/2025_05_07",
        ),
        "ocr_error_model": OCRErrorPredictor(
            device=device,
            dtype=dtype,
            checkpoint=f"{BASE_MODEL_DIR}/ocr_error_detection/2025_02_18",
        ),
    }


def create_pdf_converted():
    """Create a PDF converter with the loaded marker models."""
    print(f"Model in use : {os.listdir(BASE_MODEL_DIR)}")
    converter = PdfConverter(
        artifact_dict=load_marker_models_dict(),
    )
    print("PDF converter created with loaded models.")
    return converter


def process_pdf_via_marker(pdf_path: str, output_dir: str, filename: str):
    """Process a PDF file using the marker OCR pipeline and save the output."""
    try:
        converter = create_pdf_converted()
        rendered_ = converter(pdf_path)
        print(f"PDF {filename} processed and now saving to {output_dir}")
        save_output(rendered=rendered_, output_dir=output_dir, filename=filename)
    except Exception as e:
        print(f"Error processing PDF {filename}: {str(e)}")
        raise e
