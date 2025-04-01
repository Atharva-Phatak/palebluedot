import pulumi
import pulumi_kubernetes as k8s
import configparser
import os


def create_aws_secret(
    provider: k8s.Provider,
    depends_on: list = None,
    namespace: str = "pipeline_namespace",
):
    aws_credentials_path = os.path.expanduser("~/.aws/credentials")

    if not os.path.exists(aws_credentials_path):
        raise FileNotFoundError(
            f"AWS credentials file not found at {aws_credentials_path}"
        )
    # Read credentials from the file
    config = configparser.ConfigParser()
    config.read(aws_credentials_path)

    # Get credentials from the default profile (or specify a different profile if needed)
    profile = "default"  # Change this if you want to use a different profile
    aws_access_key = config.get(profile, "aws_access_key_id")
    aws_secret_key = config.get(profile, "aws_secret_access_key")

    aws_region = "us-east-1"  # Default region
    if config.has_option(profile, "region"):
        aws_region = config.get(profile, "region")

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
