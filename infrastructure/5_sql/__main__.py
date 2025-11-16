import pulumi
from infrastructure.helper.config import load_config
from infrastructure.helper.provider import get_k8s_provider
from infrastructure.components.sql.deploy_sql import deploy_mysql

config = load_config()
pconfig = pulumi.Config()
namespace_name = pconfig.require("namespace")


provider = get_k8s_provider()
mysql_resource = deploy_mysql(
    k8s_provider=provider,
    namespace=namespace_name,
    cfg=config,
    depends_on=[],
)
