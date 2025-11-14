import pulumi
import pulumi_kubernetes as k8s
from infrastructure.helper.infisical_client import get_infiscal_sdk
import secrets
import string
from infrastructure.helper.constants import SecretNames


def generate_password(length: int = 32):
    """Generate password"""
    chars = string.ascii_letters + string.digits + string.punctuation
    return "".join(secrets.choice(chars) for _ in range(length))


def generate_sensible_access_key(app_name: str, user_name: str, suffix_length: int = 6):
    """
    Generates a human-readable, sensible MinIO access key.
    Example output: MINIO-USER-A1B2C3
    """
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(secrets.choice(chars) for _ in range(suffix_length))
    return f"{app_name.upper()}-{user_name.upper()}-{suffix}"


def get_secret(access_key_identifier: str, project_id: str, environment_slug: str):
    """Retrieve the Postgres password from the secret manager."""
    client = get_infiscal_sdk()
    _secret = client.secrets.get_secret_by_name(
        secret_name=access_key_identifier,
        project_id=project_id,
        environment_slug=environment_slug,
        secret_path="/",
    )
    return _secret.secretValue


def create_infiscal_secret(
    project_id: str, environment_slug: str, secret_name: str, secret_value: str
):
    """Method to create secret via infiscal."""
    client = get_infiscal_sdk()
    _secret = client.secrets.create_secret_by_name(
        secret_name=secret_name,
        project_id=project_id,
        environment_slug=environment_slug,
        secret_value=secret_value,
    )
    return _secret.secretValue


def generate_minio_secret(project_id: str, environment_slug: str):
    minio_access_key = generate_sensible_access_key(
        app_name="minio", user_name="atharva"
    )
    minio_secret_key = generate_minio_secret()
    minio_access_key = create_infiscal_secret(
        project_id=project_id,
        environment_slug=environment_slug,
        secret_name=SecretNames.MINIO_ACCESS_KEY.value,
        secret_value=minio_access_key,
    )
    minio_secret_key = create_infiscal_secret(
        project_id=project_id,
        environment_slug=environment_slug,
        secret_name=SecretNames.MINIO_SECRET_KEY.value,
        secret_value=minio_secret_key,
    )


def create_aws_secret(
    provider: k8s.Provider,
    namespace: str,
    project_id: str,
    depends_on: list = None,
):
    aws_access_key = get_secret(
        access_key_identifier="minio_access_key",
        project_id=project_id,
        environment_slug="dev",
    )
    aws_secret_key = get_secret(
        access_key_identifier="minio_secret_key",
        project_id=project_id,
        environment_slug="dev",
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


def create_gh_secret(
    namespace: str,
    project_id: str,
    depends_on: list,
    k8s_provider: k8s.Provider,
    environment_slug: str = "dev",
):
    github_token = get_secret(
        access_key_identifier="gh_token",
        project_id=project_id,
        environment_slug=environment_slug,
    )
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


def create_postgres_secret(
    namespace: str,
    project_id: str,
    environment_slug: str,
    access_key_identifier: str,
    k8s_provider: k8s.Provider,
    depends_on: list = None,
):
    postgres_password = get_secret(
        project_id=project_id,
        environment_slug=environment_slug,
        access_key_identifier=access_key_identifier,
    )

    postgres_secret = k8s.core.v1.Secret(
        "metaflow-db-secret",
        metadata={
            "name": "metaflow-db-secret",
            "namespace": namespace,  # Same namespace as the Helm chart
        },
        string_data={"postgres-password": postgres_password},
        opts=pulumi.ResourceOptions(
            provider=k8s_provider, depends_on=depends_on if depends_on else []
        ),
    )
    return postgres_secret


def create_slack_secret(
    namespace: str,
    depends_on: list,
    project_id: str,
    k8s_provider: k8s.Provider,
    environment_slug: str = "dev",
):
    slack_token = get_secret(
        access_key_identifier="slack_token",
        project_id=project_id,
        environment_slug=environment_slug,
    )
    slack_secret = k8s.core.v1.Secret(
        "slack-secret",
        metadata={
            "name": "slack-secret",
            "namespace": namespace,
        },
        string_data={"SLACK_TOKEN": slack_token},
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=depends_on),
    )
    return slack_secret


def create_mistral_api_secret(
    namespace: str,
    depends_on: list,
    project_id: str,
    k8s_provider: k8s.Provider,
    environment_slug: str = "dev",
):
    mistral_token = get_secret(
        access_key_identifier="MISTRAL_TOKEN",
        project_id=project_id,
        environment_slug=environment_slug,
    )
    mistral_secret = k8s.core.v1.Secret(
        "mistral-secret",
        metadata={
            "name": "mistral-secret",
            "namespace": namespace,
        },
        string_data={"MISTRAL_TOKEN": mistral_token},
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=depends_on),
    )
    return mistral_secret


def create_argilla_secret(
    namespace: str,
    argilla_access_key_identifier: str,
    argilla_secret_key_identifier: str,
    argilla_api_key_identifier: str,
    k8s_provider: k8s.Provider,
    project_id: str,
    depends_on: list = None,
    environment_slug: str = "dev",
):
    argilla_access_key = get_secret(
        access_key_identifier=argilla_access_key_identifier,
        project_id=project_id,
        environment_slug=environment_slug,
    )
    argilla_secret_key = get_secret(
        access_key_identifier=argilla_secret_key_identifier,
        project_id=project_id,
        environment_slug=environment_slug,
    )
    argilla_api_key = get_secret(
        access_key_identifier=argilla_api_key_identifier,
        project_id=project_id,
        environment_slug=environment_slug,
    )
    argilla_secret = k8s.core.v1.Secret(
        "argilla-auth-secret",
        metadata={
            "name": "argilla-auth-secret",
            "namespace": namespace,
        },
        string_data={
            "argilla_username": argilla_access_key,
            "argilla_password": argilla_secret_key,
            "argilla_apiKey": argilla_api_key,
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=depends_on),
    )
    return argilla_secret
