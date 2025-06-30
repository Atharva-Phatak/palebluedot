import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import Namespace


def deploy_minio_sensor(
    namespace: Namespace,
    provider: k8s.Provider,
    depends_on: list,
):
    """
    Sensor that captures MinIO file upload events and sends metadata to Metaflow webhook.
    """
    metaflow_webhook_url = (
        "http://metaflow-webhook-service.metaflow.svc.cluster.local:12000/argoevent"
    )

    minio_sensor = k8s.apiextensions.CustomResource(
        "minio-file-sensor",
        api_version="argoproj.io/v1alpha1",
        kind="Sensor",
        metadata={
            "name": "minio-file-sensor",
            "namespace": namespace.metadata.name,
        },
        spec={
            "eventBusName": "default",
            "dependencies": [
                {
                    "name": "minio-dep",
                    "eventSourceName": "minio-event-source",
                    "eventName": "data-upload",
                }
            ],
            "triggers": [
                {
                    "template": {
                        "name": "send-metaflow-event",
                        "http": {
                            "url": metaflow_webhook_url,
                            "method": "POST",
                            "payload": [  # <-- THIS must be used, not 'parameters'
                                {
                                    "src": {
                                        "dependencyName": "minio-dep",
                                        "dataKey": "notification.0.s3.object.key",
                                    },
                                    "dest": "file_name",
                                },
                                {
                                    "src": {
                                        "dependencyName": "minio-dep",
                                        "dataKey": "notification.0.s3.object.size",
                                    },
                                    "dest": "file_size",
                                },
                                {
                                    "src": {
                                        "dependencyName": "minio-dep",
                                        "dataKey": "notification.0.s3.bucket.name",
                                    },
                                    "dest": "bucket_name",
                                },
                                {
                                    "src": {
                                        "dependencyName": "minio-dep",
                                        "dataKey": "notification.0.eventTime",
                                    },
                                    "dest": "upload_time",
                                },
                            ],
                        },
                    }
                }
            ],
        },
        opts=pulumi.ResourceOptions(
            provider=provider,
            depends_on=depends_on,
            custom_timeouts=pulumi.CustomTimeouts(create="10m"),
        ),
    )

    return minio_sensor
