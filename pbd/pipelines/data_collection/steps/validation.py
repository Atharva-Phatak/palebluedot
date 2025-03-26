import pydantic


class ExtractedData(pydantic.BaseModel):
    title: str
    extension: str
    links: list[str]
