import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.core.v1 import Namespace


def deploy_minio_sensor(
    namespace: Namespace,
    provider: k8s.Provider,
    depends_on: list,
):
    """
    Creates a sensor that captures MinIO file upload events and logs file details.
    The sensor will log the file name, size, bucket, and other metadata.
    """
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
                        "name": "log-file-info",
                        "log": {
                            "intervalSeconds": 1,
                        },
                    },
                    "parameters": [
                        {
                            "src": {
                                "dependencyName": "minio-dep",
                                "dataKey": "notification.0.s3.object.key",
                            },
                            "dest": "file-name",
                        },
                        {
                            "src": {
                                "dependencyName": "minio-dep",
                                "dataKey": "notification.0.s3.object.size",
                            },
                            "dest": "file-size",
                        },
                        {
                            "src": {
                                "dependencyName": "minio-dep",
                                "dataKey": "notification.0.s3.bucket.name",
                            },
                            "dest": "bucket-name",
                        },
                        {
                            "src": {
                                "dependencyName": "minio-dep",
                                "dataKey": "notification.0.eventTime",
                            },
                            "dest": "upload-time",
                        },
                        {
                            "src": {
                                "dependencyName": "minio-dep",
                                "dataKey": "notification.0.eventName",
                            },
                            "dest": "event-type",
                        },
                    ],
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
