from applications.metaflow.deploy_metaflow import create_metaflow_config


def deploy_metaflow_config_component(
    depends_on: list, metaflow_config: dict, argo_config: dict
):
    full_metaflow_config = metaflow_config | argo_config
    create_metaflow_config(config=full_metaflow_config, depends_on=depends_on)
