from metaflow.integrations import ArgoEvent
import uuid
import logging
from pbd.webhooks.metaflow_webhook.config import settings


def get_event_name_map(event_name: str):
    event_name_map = {
        "s3:ObjectCreated:Put": "minio.upload",
        "s3:ObjectRemoved:Delete": "data-delete",
        # Add more mappings as needed
    }
    return event_name_map.get(event_name, event_name)


def publish_event(data: dict):
    event_name = data.get("event_name")
    if not event_name:
        raise ValueError("Event name is required in the data")
    print(f"Received data: {data}")
    payload = {
        "filename": data.get("filename", "unknown"),
        "file_size": data.get("file_size", "0"),
        "bucket_name": data.get("bucket_name", "unknown"),
        "upload_time": data.get("upload_time", "unknown"),
        "originator": data.get("originator", "argo-events"),
        "event_id": str(uuid.uuid4()),
    }
    print(f"Publishing event '{event_name}' with payload: {payload}")
    logging.info(f"Publishing event '{event_name}' with payload: {payload}")
    event_name = get_event_name_map(event_name)
    event = ArgoEvent(
        name=event_name,
        payload=payload,
        url=settings.METAFLOW_WEBHOOK_URL,
    )
    return event.publish()
