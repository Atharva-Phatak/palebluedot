import pulumi_minio as pm
import pulumi_kubernetes as k8s
import pulumi


def deploy_minio_buckets(
    depends_on: list, minio_ingress: k8s.networking.v1beta1.Ingress
):
    minio_access_key = "minio@1234"
    minio_secret_key = "minio@local1234"
    minio_ingress_host = "fsml-minio.info"
    # Create a bucket
    minio_provider = pm.Provider(
        "minio-provider",
        minio_server=minio_ingress_host,
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
