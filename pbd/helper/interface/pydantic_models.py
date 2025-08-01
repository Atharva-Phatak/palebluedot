import pydantic
from typing import Optional


class DataProcessingPipelineConfig(pydantic.BaseModel):
    bucket_name: str
    filepath: str
    output_path: str
    slack_channel: str
    image_dpi: int = 300
    endpoint: str = "http://minio-palebluedot.io"
    use_mistral: bool = False


class OCRModelParams(pydantic.BaseModel):
    max_tokens: int
    temperature: float


class PostProcessingParams(pydantic.BaseModel):
    temperature: float
    top_p: float
    max_tokens: int
    top_k: Optional[int] = None


class OCRPipelineConfig(pydantic.BaseModel):
    minio_endpoint: str
    ocr_model_path: str
    ocr_params: OCRModelParams
    ocr_model_batch_size: int

    filename: str
    raw_data_path: str
    bucket: str
    run_test: bool = False


class OCRPostProcessPipelineConfig(pydantic.BaseModel):
    minio_endpoint: str
    filename: str
    bucket: str
    max_model_len: int = 16384
    post_processing_model_path: str
    post_processing_params: PostProcessingParams
    post_processing_batch_size: int
    run_test: bool = False
