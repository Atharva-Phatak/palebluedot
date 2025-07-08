import pydantic
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
class PageResponse(pydantic.BaseModel):
    primary_language: Optional[str]
    is_rotation_valid: Optional[bool]
    rotation_correction: Optional[int]
    is_table: Optional[bool]
    is_diagram: Optional[bool]
    natural_text: Optional[str]

    model_config = pydantic.ConfigDict(extra="allow")
