import os
import subprocess
import pulumi
import pulumi_kubernetes as k8s
from pulumi_kubernetes.helm.v3 import LocalChartOpts
import infrastructure.helper.secrets as secrets_helper
from infrastructure.helper.constants import SecretNames


def download_zenml_helm_chart():
    # Download the chart directly from GitHub
    chart_version = "0.91.0"  # Replace with your desired version
    chart_url = (
        f"https://github.com/zenml-io/zenml/archive/refs/tags/{chart_version}.zip"
    )
    download_path = f"/tmp/zenml-{chart_version}.zip"
    extract_path = f"/tmp/zenml-{chart_version}"
    chart_path = f"{extract_path}/zenml-{chart_version}/helm"

    # Download and extract if not already done
    if not os.path.exists(chart_path):
        subprocess.run(["curl", "-L", chart_url, "-o", download_path], check=True)
        subprocess.run(["unzip", "-q", download_path, "-d", extract_path], check=True)

    return chart_path


def deploy_zenml(
    depends_on: list,
    k8s_provider: k8s.Provider,
    namespace: str,
    infiscal_project_id: str,
    environment_slug: str,
) -> k8s.helm.v3.Chart:
    # Generate and store the JWT secret
    jwt_secret = secrets_helper.generate_zenml_jwt_secret(
        project_id=infiscal_project_id,
        environment_slug=environment_slug,
    )
    zenml_sql_user = secrets_helper.get_secret(
        access_key_identifier=SecretNames.MYSQL_USER.value,
        project_id=infiscal_project_id,
        environment_slug=environment_slug,
    )
    zenml_sql_password = secrets_helper.get_secret(
        access_key_identifier=SecretNames.MYSQL_PASSWORD.value,
        project_id=infiscal_project_id,
        environment_slug=environment_slug,
    )

    chart_path = download_zenml_helm_chart()
    helm_chart = k8s.helm.v3.Chart(
        "zenml-server",
        config=LocalChartOpts(
            path=chart_path,
            values={
                "zenml": {
                    "analyticsOptIn": False,
                    "auth": {
                        "authType": "OAUTH2_PASSWORD_BEARER",
                        "jwtSecretKey": str(jwt_secret),
                        "jwtTokenAlgorithm": "HS256",
                        "jwtTokenIssuer": "",
                        "jwtTokenAudience": "",
                        "jwtTokenLeewaySeconds": 10,
                        "jwtTokenExpireMinutes": 120,  # Increased from default to prevent frequent logouts
                        "authCookieName": "",
                        "authCookieDomain": "",
                        "corsAllowOrigins": ["*"],
                        "maxFailedDeviceAuthAttempts": 5,  # Increased to reduce accidental lockouts
                        "deviceAuthTimeout": 600,  # Increased timeout to allow more time for auth
                        "deviceAuthPollingInterval": 10,  # Adjusted for better polling rate
                        "deviceExpirationMinutes": 10080,  # 1 week (adjust as needed)
                        "trustedDeviceExpirationMinutes": 20160,  # 14 days for trusted devices
                        "externalLoginURL": "",
                        "externalUserInfoURL": "",
                        "externalServerID": "",
                        "rbacImplementationSource": "",
                        "featureGateImplementationSource": "",
                    },
                    "database": {
                        # MySQL connection URL without password
                        "url": f"mysql://{zenml_sql_user}:{zenml_sql_password}@mysql-chart.{namespace}.svc.cluster.local:3306/zenml",
                        # Reference to the Kubernetes secret for password
                        "passwordSecretRef": {
                            "name": "mysql-secret",
                            "key": "mysql-password",
                        },
                    },
                    "backupSecretsStore": {"enabled": False},
                    "ingress": {
                        "enabled": True,
                        "host": "zenml-slm.io",
                        "annotations": {
                            "nginx.ingress.kubernetes.io/rewrite-target": "/",
                            "nginx.ingress.kubernetes.io/ssl-redirect": "false",
                            "nginx.ingress.kubernetes.io/proxy-body-size": "64m",
                            "nginx.ingress.kubernetes.io/proxy-connect-timeout": "300",
                            "nginx.ingress.kubernetes.io/proxy-send-timeout": "300",
                            "nginx.ingress.kubernetes.io/proxy-read-timeout": "300",
                        },
                    },
                },
                "resources": {
                    "limits": {
                        "cpu": "300m",
                        "memory": "2Gi",
                    },
                    "requests": {
                        "cpu": "200m",
                        "memory": "512Mi",
                    },
                },
            },
            namespace=namespace,
        ),
        opts=pulumi.ResourceOptions(
            provider=k8s_provider,
            custom_timeouts=pulumi.CustomTimeouts(create="20m"),
            depends_on=depends_on,
        ),
    )
    pulumi.export("zenml_service", helm_chart.ready)
    return helm_chart
