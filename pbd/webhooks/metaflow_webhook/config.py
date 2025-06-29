from pydantic import BaseSettings


class Settings(BaseSettings):
    METAFLOW_WEBHOOK_URL: str = (
        "http://metaflow-service.metaflow.svc.cluster.local:8080/events"
    )


settings = Settings()
