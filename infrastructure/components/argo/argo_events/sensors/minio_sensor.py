import pulumi
import pulumi_kubernetes as k8s


def deploy_minio_sensor(
    namespace: str,
    provider: k8s.Provider,
    depends_on: list,
):
    """
    Sensor that captures MinIO file upload events and sends metadata to Metaflow webhook.
    Only triggers for .pdf files in 'raw_data/'.
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
            "namespace": namespace,
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
                            "payload": [
                                {
                                    "src": {
                                        "dependencyName": "minio-dep",
                                        "dataKey": "notification.0.s3.object.key",
                                    },
                                    "dest": "filename",
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
                                {
                                    "src": {
                                        "dependencyName": "minio-dep",
                                        "dataKey": "notification.0.eventName",
                                    },
                                    "dest": "event_name",
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
