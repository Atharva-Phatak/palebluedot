import pydantic
from dataclasses import dataclass
from typing import Optional


class DataProcessingPipelineConfig(pydantic.BaseModel):
    bucket_name: str
    filepath: str
    output_path: str
    slack_channel: str
    image_dpi: int = 300
    endpoint: str = "http://minio-palebluedot.io"


class OCRModelParams(pydantic.BaseModel):
    max_tokens: int


class PostProcessingParams(pydantic.BaseModel):
    temperature: float
    top_p: float
    top_k: int
    max_tokens: int


class OCRPipelineConfig(pydantic.BaseModel):
    minio_endpoint: str
    image_path: str
    local_path: str
    extract_to: str
    ocr_model_path: str
    ocr_params: OCRModelParams
    ocr_model_batch_size: int
    post_processing_model_path: str
    post_processing_params: PostProcessingParams
    post_processing_batch_size: int
    filename: str
    extracted_zip_path: str
    bucket: str
    run_test: bool = False


# OCR flux specific models
@dataclass(frozen=True)
class PageResponse:
    primary_language: Optional[str]
    is_rotation_valid: Optional[bool]
    rotation_correction: Optional[int]
    is_table: Optional[bool]
    is_diagram: Optional[bool]
    natural_text: Optional[str]

    model_config = pydantic.ConfigDict(extra="allow")

    def __post_init__(self):
        # Validate rotation_correction is one of the allowed values
        if self.rotation_correction not in {0, 90, 180, 270}:
            raise ValueError("rotation_correction must be one of [0, 90, 180, 270].")

        # Type checks
        if not isinstance(self.primary_language, (str, type(None))):
            raise TypeError("primary_language must be of type Optional[str].")
        if not isinstance(self.is_rotation_valid, bool):
            raise TypeError("is_rotation_valid must be of type bool.")
        if not isinstance(self.rotation_correction, int):
            raise TypeError("rotation_correction must be of type int.")
        if not isinstance(self.is_table, bool):
            raise TypeError("is_table must be of type bool.")
        if not isinstance(self.is_diagram, bool):
            raise TypeError("is_diagram must be of type bool.")
        if not isinstance(self.natural_text, (str, type(None))):
            raise TypeError("natural_text must be of type Optional[str].")
