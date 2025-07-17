from pbd.helper.slack import send_slack_message
from metaflow import user_step_decorator


@user_step_decorator
def notify_slack_on_success(step_name,
                            flow,
                            inputs=None,
                            attributes=None):
    """Decorator to notify Slack on successful completion of a step."""
    yield
    send_slack_message(
        token=flow.slack_token,
        message=f"Step `{step_name}` in flow `{flow.name}` completed successfully.",
        channel="#zeml-pipelines",
    )
