from infisical_sdk import InfisicalSDKClient


def get_infiscal_sdk() -> InfisicalSDKClient:
    # Initialize the client
    client = InfisicalSDKClient(host="https://app.infisical.com")

    # Authenticate (example using Universal Auth)
    client.auth.universal_auth.login(
        client_id="c570b884-e978-4e0e-84b9-4565669ac91e",
        client_secret="2fa723668b51a29dabef65b606713d29b7fe75cfc62b1d11913e7208e1c52b38",
    )

    return client
