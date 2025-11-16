from infisical_sdk import InfisicalSDKClient
import os


def get_infiscal_sdk() -> InfisicalSDKClient:
    # Initialize the client
    client = InfisicalSDKClient(host="https://app.infisical.com")
    client_id = os.getenv("INFISICAL_CLIENT_ID")
    client_secret = os.getenv("INFISICAL_SECRET")
    # Authenticate (example using Universal Auth)
    client.auth.universal_auth.login(
        client_id=client_id,
        client_secret=client_secret,
    )

    return client
