from metaflow.integrations import ArgoEvent
import uuid
import logging
from pbd.webhooks.metaflow_webhook.config import settings


def publish_event(data: dict):
    event_name = data.get("event", "minio.upload")
    payload = {
        "file_name": data.get("file_name", "unknown"),
        "file_size": data.get("file_size", "0"),
        "bucket_name": data.get("bucket_name", "unknown"),
        "upload_time": data.get("upload_time", "unknown"),
        "originator": data.get("originator", "argo-events"),
        "event_id": str(uuid.uuid4()),
    }

    logging.info(f"Publishing event '{event_name}' with payload: {payload}")
    event = ArgoEvent(
        name=event_name,
        payload=payload,
        url=settings.METAFLOW_WEBHOOK_URL,
    )
    return event.publish()
