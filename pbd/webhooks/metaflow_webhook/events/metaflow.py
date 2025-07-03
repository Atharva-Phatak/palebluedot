from metaflow.integrations import ArgoEvent
import uuid
import logging
from pbd.webhooks.metaflow_webhook.config import settings
import pbd.helper.s3_paths as config_paths


def get_config_uri_based_on_event(event_name: str):
    if event_name == "minio.upload":
        return config_paths.data_processing_pipeline_config_path()
    else:
        raise ValueError(f"Unsupported event name: {event_name}")


def publish_event(data: dict):
    event_name = data.get("event")
    logging.info(f"Received data: {data}")

    config_path = get_config_uri_based_on_event(event_name=event_name)
    payload = {
        "filename": data.get("file_name", "unknown"),
        "file_size": data.get("file_size", "0"),
        "bucket_name": data.get("bucket_name", "unknown"),
        "upload_time": data.get("upload_time", "unknown"),
        "originator": data.get("originator", "argo-events"),
        "config_uri": config_path,
        "event_id": str(uuid.uuid4()),
    }
    print(f"Publishing event '{event_name}' with payload: {payload}")
    logging.info(f"Publishing event '{event_name}' with payload: {payload}")
    event = ArgoEvent(
        name=event_name,
        payload=payload,
        url=settings.METAFLOW_WEBHOOK_URL,
    )
    return event.publish()
