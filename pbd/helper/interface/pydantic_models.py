import pydantic


class DataProcessingPipelineConfig(pydantic.BaseModel):
    bucket_name: str
    filepath: str
    output_path: str
    slack_channel: str
    image_dpi: int = 300
    endpoint: str = "http://minio-palebluedot.io"
