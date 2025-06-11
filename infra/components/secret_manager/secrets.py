import os

import pulumi
import pulumi_kubernetes as k8s
from components.minio.minio import get_minio_secret


def create_aws_secret(
    provider: k8s.Provider,
    infiscal_project_id: str,
    depends_on: list = None,
    namespace: str = "pipeline_namespace",
):
    # Get credentials from the default profile (or specify a different profile if needed) -> we are using minio details as to hoax aws credentials
    aws_access_key, aws_secret_key = get_minio_secret(
        access_key_identifier="minio_access_key",
        secret_key_identifier="minio_secret_key",
        environment_slug="dev",
        project_id=infiscal_project_id,
    )
    aws_region = "us-east-1"  # Default region
    aws_credentials_secret = k8s.core.v1.Secret(
        "aws-credentials",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="aws-credentials", namespace=namespace
        ),
        string_data={
            "AWS_ACCESS_KEY_ID": aws_access_key,
            "AWS_SECRET_ACCESS_KEY": aws_secret_key,
            "AWS_REGION": aws_region,
        },
        opts=pulumi.ResourceOptions(parent=provider, depends_on=depends_on),
    )
    return aws_credentials_secret


def create_gh_secret(namespace: str, depends_on: list, k8s_provider: k8s.Provider):
    github_token = os.environ.get("GITHUB_TOKEN")
    github_secret = k8s.core.v1.Secret(
        "gha-rs-github-secret",
        metadata={
            "name": "gha-rs-github-secret",
            "namespace": namespace,
        },
        string_data={"github_token": github_token},
        opts=pulumi.ResourceOptions(provider=k8s_provider),
    )
    return github_secret
