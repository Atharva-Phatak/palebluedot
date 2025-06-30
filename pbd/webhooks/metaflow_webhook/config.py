import pydantic


class Settings(pydantic.BaseModel):
    METAFLOW_WEBHOOK_URL: str = (
        "http://argo-events-webhook-eventsource-svc:12000/metaflow-event"
    )


settings = Settings()
