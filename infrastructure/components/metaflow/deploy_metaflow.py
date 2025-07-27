import json
import typing as T

import pulumi
import pulumi_command as command
import pulumi_kubernetes as k8s
from infrastructure.helper.secrets import get_secret
from pulumi import ResourceTransformationResult
from pulumi_kubernetes.helm.v3 import Chart, ChartOpts, FetchOpts


def create_metaflow_config(
    config: T.Dict[str, T.Any],
    config_name: str = "metaflow-config",
    depends_on: T.Optional[list] = None,
) -> command.local.Command:
    """
    Create a Pulumi Command resource to write Metaflow configuration file.

    Args:
        config: Dictionary containing Metaflow configuration
        config_name: Name for the Pulumi resource
        depends_on: List of resources this command depends on

    Returns:
        pulumi_command.local.Command resource
    """

    # Convert config to JSON string for the command
    config_json = json.dumps(config, indent=2)

    # Create the command to write config file
    config_writer = command.local.Command(
        config_name,
        create=pulumi.Output.concat(
            "mkdir -p ~/.metaflowconfig && ",
            "cat > ~/.metaflowconfig/config.json << 'EOF'\n",
            config_json,
            "\nEOF",
        ),
        # Optional: Define what to do on delete
        delete="echo '🗑️ Metaflow config cleanup (if needed)'",
        opts=pulumi.ResourceOptions(depends_on=depends_on or []),
    )

    return config_writer


def deploy_metaflow(
    k8s_provider: k8s.Provider,
    namespace: str,
    infiscal_project_id: str,
    environment_slug: str,
    access_key_identifier: str,
    aws_access_key_identifier: str,
    aws_secret_key_identifier: str,
    depends_on: list = None,
):
    postgres_password = get_secret(
        project_id=infiscal_project_id,
        environment_slug=environment_slug,
        access_key_identifier=access_key_identifier,
    )
    minio_access_key = get_secret(
        access_key_identifier=aws_access_key_identifier,
        project_id=infiscal_project_id,
        environment_slug=environment_slug,
    )
    minio_secret_key = get_secret(
        access_key_identifier=aws_secret_key_identifier,
        project_id=infiscal_project_id,
        environment_slug=environment_slug,
    )
    metaflow_service = Chart(
        "metaflow-service",
        ChartOpts(
            chart="metaflow-service",
            namespace=namespace,
            fetch_opts=FetchOpts(repo="https://outerbounds.github.io/metaflow-tools"),
            values={
                "metadatadb": {
                    "user": "metaflow",
                    "password": postgres_password,
                    "name": "metaflow",
                    "host": "metaflow-postgres-postgresql.metaflow.svc.cluster.local",
                },
                "image": {
                    "repository": "public.ecr.aws/outerbounds/metaflow_metadata_service",
                    "tag": "2.4.13-2-g70af4ed",
                },
                "ingress": {
                    "enabled": True,
                    "className": "nginx",
                    "annotations": {
                        "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                        "nginx.ingress.kubernetes.io/rewrite-target": "/",
                        "nginx.ingress.kubernetes.io/proxy-body-size": "64m",
                        "nginx.ingress.kubernetes.io/proxy-connect-timeout": "300",
                        "nginx.ingress.kubernetes.io/proxy-send-timeout": "300",
                        "nginx.ingress.kubernetes.io/proxy-read-timeout": "300",
                    },
                    "hosts": [
                        {
                            "host": "svc.mflow.palebluedot.io",
                            "paths": [
                                {"path": "/", "pathType": "ImplementationSpecific"}
                            ],
                        }
                    ],
                    "tls": [],
                },
                "resources": {
                    "requests": {"cpu": "25m", "memory": "64Mi"},
                    "limits": {"cpu": "50m", "memory": "128Mi"},
                },
            },
        ),
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            custom_timeouts=pulumi.CustomTimeouts(create="10m"),
            depends_on=depends_on,
        ),
    )
    depends_on = depends_on + [metaflow_service] if depends_on else [metaflow_service]
    metaflow_ui = Chart(
        "metaflow-ui",
        ChartOpts(
            chart="metaflow-ui",
            namespace=namespace,
            fetch_opts=FetchOpts(repo="https://outerbounds.github.io/metaflow-tools"),
            values={
                # Force namespace override in the chart values
                "fullnameOverride": "metaflow-ui",
                "nameOverride": "metaflow-ui",
                "uiBackend": {
                    "metadatadb": {
                        "user": "metaflow",
                        "password": postgres_password,
                        "name": "metaflow",
                        "host": "metaflow-postgres-postgresql.metaflow.svc.cluster.local",
                    },
                    "metaflowDatastoreSysRootS3": "s3://metaflow",
                    "metaflowS3EndpointURL": "http://minio-palebluedot.io",
                    "image": {
                        "name": "public.ecr.aws/outerbounds/metaflow_metadata_service",
                        "tag": "2.4.13-2-g70af4ed",
                    },
                    "env": [
                        {"name": "AWS_ACCESS_KEY_ID", "value": minio_access_key},
                        {"name": "AWS_SECRET_ACCESS_KEY", "value": minio_secret_key},
                        {"name": "MF_METADATA_DB_SSL_MODE", "value": "prefer"},
                    ],
                    "resources": {"requests": {"cpu": "100m", "memory": "256Mi"}},
                },
                "uiStatic": {
                    "metaflowUIBackendURL": "http://ui.mflow.palebluedot.io/api",
                    "image": {
                        "name": "public.ecr.aws/outerbounds/metaflow_ui",
                        "tag": "v1.3.13-5-g5dd049e",
                    },
                    "resources": {
                        "requests": {"cpu": "25m", "memory": "64Mi"},
                        "limits": {"cpu": "50m", "memory": "256Mi"},
                    },
                },
                "ingress": {
                    "enabled": True,
                    "className": "nginx",  # adjust for your ingress controller
                    "annotations": {
                        "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                        "nginx.ingress.kubernetes.io/proxy-body-size": "64m",
                        "nginx.ingress.kubernetes.io/proxy-connect-timeout": "300",
                        "nginx.ingress.kubernetes.io/proxy-send-timeout": "300",
                        "nginx.ingress.kubernetes.io/proxy-read-timeout": "300",
                    },
                    "hosts": [
                        {
                            "host": "ui.mflow.palebluedot.io",
                            "paths": [
                                {"path": "/api", "pathType": "Prefix"},
                                {"path": "/static", "pathType": "Prefix"},
                                {"path": "/", "pathType": "Prefix"},
                            ],
                        }
                    ],
                },
            },
        ),
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            custom_timeouts=pulumi.CustomTimeouts(create="10m"),
            depends_on=depends_on,
            transformations=[
                lambda args: (
                    ResourceTransformationResult(
                        props={
                            **args.props,
                            "metadata": {
                                **args.props.get("metadata", {}),
                                "namespace": namespace,
                            },
                        },
                        opts=args.opts,
                    )
                    if args.type_.startswith("kubernetes:")
                    else None
                )
            ],
        ),
    )
    pulumi.export("metaflow-service-status", metaflow_service.ready)
    pulumi.export("metaflow-ui-status", metaflow_ui.ready)
    metaflow_config = {
        "METAFLOW_KUBERNETES_NAMESPACE": "metaflow",
        "METAFLOW_DEFAULT_DATASTORE": "s3",
        "METAFLOW_S3_ENDPOINT_URL": "http://minio-palebluedot.io",
        "METAFLOW_DATASTORE_SYSROOT_S3": "s3://metaflow",
        "METAFLOW_DEFAULT_METADATA": "service",
        "METAFLOW_SERVICE_URL": "http://svc.mflow.palebluedot.io",
        "METAFLOW_SERVICE_INTERNAL_URL": "http://metaflow-service.metaflow.svc.cluster.local:8080",
        "METAFLOW_UI_URL": "http://ui.mflow.palebluedot.io",
    }
    return metaflow_ui, metaflow_config
