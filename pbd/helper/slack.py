from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def send_slack_message(
    token: str, message: str, channel: str = "#zeml-pipelines"
) -> bool:
    """
    Send a Slack message using the official Slack SDK.

    Args:
        token (str): Slack bot token (xoxb-...).
        channel (str): Slack channel ID or name (e.g. '#general').
        message (str): The message to send.

    Returns:
        bool: True if message was sent successfully, False otherwise.
    """
    client = WebClient(token=token)

    try:
        response = client.chat_postMessage(channel=channel, text=message)
        return response["ok"]
    except SlackApiError as e:
        print(f"Slack API error: {e.response['error']}")
        return False
