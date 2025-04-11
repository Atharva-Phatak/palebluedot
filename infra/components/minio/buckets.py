import pulumi_minio as pm
import pulumi
from components.minio.minio import get_minio_secret
from helper.constant import Constants

def deploy_minio_buckets(
    depends_on: list,
):
    minio_access_key, minio_secret_key = get_minio_secret()
    # Create a bucket
    minio_provider = pm.Provider(
        "minio-provider",
        minio_server=Constants.minio_ingress_host,
        minio_user=minio_access_key,
        minio_password=minio_secret_key,

    )
    data_bucket = pm.S3Bucket(
        "data-bucket",
        bucket="data-bucket",
        opts=pulumi.ResourceOptions(depends_on=depends_on, provider=minio_provider),
    )
    zenml_bucket = pm.S3Bucket(
        "zenml-bucket",
        bucket="zenml-bucket",
        opts=pulumi.ResourceOptions(depends_on=depends_on, provider=minio_provider),
    )
    pulumi.export("data_bucket", data_bucket.bucket)
    pulumi.export("zenml_bucket", zenml_bucket.bucket)
