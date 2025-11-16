import pulumi
import pulumi_kubernetes as k8s
from infrastructure.helper.infisical_client import get_infiscal_sdk
import secrets
import string
from infrastructure.helper.constants import SecretNames
import os


def generate_password(length: int = 32):
    """Generate password"""
    chars = string.ascii_letters + string.digits
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
    """Create a secret via Infisical, only if it doesn't already exist."""
    client = get_infiscal_sdk()

    # Try to fetch the secret first
    try:
        existing_secret = client.secrets.get_secret_by_name(
            secret_name=secret_name,
            project_id=project_id,
            environment_slug=environment_slug,
            secret_path="/",  # same path you would use for creation
        )
        if existing_secret:
            print(f"⚠️ Secret '{secret_name}' already exists. Skipping creation.")
            return existing_secret.secretValue
    except Exception:
        # If secret does not exist, SDK may throw an error. Ignore that.
        pass

    # Create secret if not found
    _secret = client.secrets.create_secret_by_name(
        secret_name=secret_name,
        project_id=project_id,
        environment_slug=environment_slug,
        secret_path="/",
        secret_value=secret_value,
    )
    print(f"✅ Secret '{secret_name}' created.")
    return _secret.secretValue


def generate_minio_secret(project_id: str, environment_slug: str):
    """Generate MinIO access and secret keys and store them in Infisical."""
    minio_access_key = generate_sensible_access_key(
        app_name="minio", user_name="atharva"
    )
    minio_secret_key = generate_password()
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
    return minio_access_key, minio_secret_key


def generate_mysql_secret(project_id: str, environment_slug: str):
    mysql_user = generate_sensible_access_key(app_name="mysql", user_name="zenml")
    mysql_password = generate_password()
    mysql_user = create_infiscal_secret(
        project_id=project_id,
        environment_slug=environment_slug,
        secret_name=SecretNames.MYSQL_USER.value,
        secret_value=mysql_user,
    )
    mysql_password = create_infiscal_secret(
        project_id=project_id,
        environment_slug=environment_slug,
        secret_name=SecretNames.MYSQL_PASSWORD.value,
        secret_value=mysql_password,
    )
    return mysql_user, mysql_password


def generate_slack_secret(project_id: str, environment_slug: str):
    slack_token = os.getenv("SLACK_TOKEN")
    slack_token = create_infiscal_secret(
        project_id=project_id,
        environment_slug=environment_slug,
        secret_name=SecretNames.SLACK_TOKEN.value,
        secret_value=slack_token,
    )
    return slack_token


def generate_gh_secret(project_id: str, environment_slug: str):
    gh_token = os.getenv("GH_TOKEN")
    gh_token = create_infiscal_secret(
        project_id=project_id,
        environment_slug=environment_slug,
        secret_name="gh_token",
        secret_value=gh_token,
    )
    return gh_token


def generate_zenml_jwt_secret(
    project_id: str,
    environment_slug: str,
):
    jwt_secret = secrets.token_hex(32)
    jwt_secret = create_infiscal_secret(
        project_id=project_id,
        environment_slug=environment_slug,
        secret_name=SecretNames.ZENML_JWT_SECRET.value,
        secret_value=jwt_secret,
    )
    return jwt_secret


def create_k8s_aws_secret(
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


def create_k8s_gh_secret(
    namespace: str,
    project_id: str,
    depends_on: list,
    k8s_provider: k8s.Provider,
    environment_slug: str = "dev",
):
    gh_token = generate_gh_secret(
        project_id=project_id,
        environment_slug=environment_slug,
    )
    github_secret = k8s.core.v1.Secret(
        "gha-rs-github-secret",
        metadata={
            "name": "gha-rs-github-secret",
            "namespace": namespace,
        },
        string_data={"github_token": gh_token},
        opts=pulumi.ResourceOptions(provider=k8s_provider),
    )
    return github_secret


def create_k8s_mysql_secret(
    namespace: str,
    project_id: str,
    environment_slug: str,
    k8s_provider: k8s.Provider,
    depends_on: list = None,
):
    mysql_password = get_secret(
        project_id=project_id,
        environment_slug=environment_slug,
        access_key_identifier=SecretNames.MYSQL_PASSWORD.value,
    )
    mysql_user = get_secret(
        project_id=project_id,
        environment_slug=environment_slug,
        access_key_identifier=SecretNames.MYSQL_USER.value,
    )

    mysql_secret = k8s.core.v1.Secret(
        "mysql-secret",
        metadata={
            "name": "mysql-secret",
            "namespace": namespace,  # Same namespace as the Helm chart
        },
        string_data={
            "mysql-password": mysql_password,
            "mysql-root-password": mysql_password,
            "mysql-replication-password": mysql_password,
            "mysql-user": mysql_user,
        },
        opts=pulumi.ResourceOptions(
            provider=k8s_provider, depends_on=depends_on if depends_on else []
        ),
    )
    return mysql_secret


def create_k8s_slack_secret(
    namespace: str,
    depends_on: list,
    project_id: str,
    k8s_provider: k8s.Provider,
    environment_slug: str = "dev",
):
    slack_token = generate_slack_secret(
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
