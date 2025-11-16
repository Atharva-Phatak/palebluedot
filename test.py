from infisical_sdk import InfisicalSDKClient

client = InfisicalSDKClient(host="https://app.infisical.com")
client_id = "54ba8c19-d4d1-41dd-a6b2-2ff2795f7fb2"
client_secret = "1e523f4f5ea10e70e936c07964f94f584bc7b1f4f4379d22ff138afed146c8c2"
# Authenticate (example using Universal Auth)
x = client.auth.universal_auth.login(
    client_id=client_id,
    client_secret=client_secret,
)
print(x)
