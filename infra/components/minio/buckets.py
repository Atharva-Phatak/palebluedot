import pulumi_minio as pm
import pulumi
from components.minio.minio import get_minio_secret

def deploy_minio_buckets(
    depends_on: list,
    buckets: list[str],
    ingress_host: str = None,
):
    minio_access_key, minio_secret_key = get_minio_secret()
    # Create a bucket
    minio_provider = pm.Provider(
        "minio-provider",
        minio_server=ingress_host,
        minio_user=minio_access_key,
        minio_password=minio_secret_key,
    )
    for bucket in buckets:
        pm.S3Bucket(
            bucket,
            bucket=bucket,
            opts=pulumi.ResourceOptions(depends_on=depends_on, provider=minio_provider),
        )
