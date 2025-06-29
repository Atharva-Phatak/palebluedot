import pydantic


class Settings(pydantic.BaseModel):
    METAFLOW_WEBHOOK_URL: str = (
        "http://metaflow-service.metaflow.svc.cluster.local:8080/events"
    )


settings = Settings()
