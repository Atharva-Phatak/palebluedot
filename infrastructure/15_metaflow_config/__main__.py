import json
import typing as T

import pulumi
import pulumi_command as command
from pulumi import StackReference


def use_config(config_dict):
    # Here, config_dict is a plain dict you can use
    # e.g., merge, pass as resource input, etc.
    return config_dict


def create_metaflow_config(
    config: T.Dict[str, T.Any],
    config_name: str = "metaflow-config",
    depends_on: T.Optional[list] = None,
) -> command.local.Command:
    """
    Create a Pulumi Command resource to write Metaflow configuration file.

    Args:
        config: Dictionary containing Metaflow configuration
        config_name: Name for the Pulumi resource
        depends_on: List of resources this command depends on

    Returns:
        pulumi_command.local.Command resource
    """

    if isinstance(config, pulumi.Output):
        # Use apply to work with the Output
        config_json = config.apply(lambda c: json.dumps(c, indent=2))
    else:
        # Regular dict - convert directly
        config_json = json.dumps(config, indent=2)

    # Create the command to write config file
    config_writer = command.local.Command(
        config_name,
        create=pulumi.Output.concat(
            "mkdir -p ~/.metaflowconfig && ",
            "cat > ~/.metaflowconfig/config.json << 'EOF'\n",
            config_json,
            "\nEOF",
        ),
        # Optional: Define what to do on delete
        delete="echo '🗑️ Metaflow config cleanup (if needed)'",
        opts=pulumi.ResourceOptions(depends_on=depends_on if depends_on else []),
    )

    return config_writer


argo_events_stack = StackReference("organization/argo_events/9_argo_events")

argo_events_config = argo_events_stack.get_output("metaflow_config")

argo_events_config = argo_events_config.apply(use_config)
create_metaflow_config(
    config=argo_events_config,
)
