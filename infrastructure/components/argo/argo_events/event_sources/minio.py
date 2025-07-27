import pulumi
import pulumi_kubernetes as k8s


def deploy_minio_event_source(
    namespace: str,
    provider: k8s.Provider,
    aws_secret: k8s.core.v1.Secret,
    depends_on: list,
):
    minio_event_source = k8s.apiextensions.CustomResource(
        "minio-event-source",
        api_version="argoproj.io/v1alpha1",
        kind="EventSource",
        metadata={
            "namespace": namespace,
            "name": "minio-event-source",
        },
        spec={
            "eventBusName": "default",
            "replicas": 1,  # Critical for event bus connection
            "minio": {
                "data-upload": {
                    "bucket": {"name": "data-bucket"},
                    "endpoint": "minio-service.metaflow.svc.cluster.local:9000",
                    "events": ["s3:ObjectCreated:Put"],
                    "filter": {"prefix": "raw_data/", "suffix": ".pdf"},
                    "insecure": True,
                    "accessKey": {
                        "key": "AWS_ACCESS_KEY_ID",
                        "name": aws_secret.metadata.name,
                    },
                    "secretKey": {
                        "key": "AWS_SECRET_ACCESS_KEY",
                        "name": aws_secret.metadata.name,
                    },
                }
            },
        },
        opts=pulumi.ResourceOptions(
            provider=provider,
            depends_on=depends_on,
            custom_timeouts=pulumi.CustomTimeouts(create="30m"),
        ),
    )

    return minio_event_source
