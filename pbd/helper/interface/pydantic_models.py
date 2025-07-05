import pydantic


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
    bucket: str
    run_test: bool = False
