from pulumi import automation as auto
import os
from pathlib import Path
import shutil


def get_base_path():
    current_file = os.path.abspath(__file__)
    base_path = os.path.abspath(os.path.join(current_file, "..", "..", ".."))
    infra_base_path = os.path.join(base_path, "palebluedot/infrastructure")
    return infra_base_path


def get_available_stacks():
    infra_base_path = get_base_path()
    stacks = [f.path for f in os.scandir(infra_base_path) if f.is_dir()]
    return sorted(stacks)


def log_only_errors(msg):
    if "diagnostic" in msg and msg["diagnostic"]["severity"] == "error":
        print("[ERROR]", msg["diagnostic"]["message"])


def deploy_stack(name, path, config=None):
    stack = auto.create_or_select_stack(stack_name=name, work_dir=path)
    for key, val in (config or {}).items():
        stack.set_config(key, auto.ConfigValue(value=val))
    stack.up(on_output=log_only_errors)
    return stack


def destroy_stack(name, path):
    stack = auto.create_or_select_stack(stack_name=name, work_dir=path)
    print(f"🗑️ Destroying stack: {name}")
    stack.destroy(on_output=print)
    return stack


def deploy_sequentially():
    infra_base_path = get_base_path()

    # Deploy cluster/namespace first
    cluster_stack = deploy_stack(
        name="1_cluster",
        path=Path(infra_base_path) / "1_cluster",
    )
    outputs = cluster_stack.outputs()  # ✅ this is a dictionary
    zenml_namespace_name = outputs["namespace"].value
    print(f"✅ Cluster and namespace deployed: {zenml_namespace_name}")
    # Deploy arc runner
    _ = deploy_stack(
        name="7_arc_runner",
        path=Path(infra_base_path) / "7_arc_runner",
    )
    # Deploy minio
    _ = deploy_stack(
        name="4_minio",
        path=Path(infra_base_path) / "4_minio",
        config={"namespace": zenml_namespace_name},
    )
    # Deploy postgres
    _ = deploy_stack(
        name="5_sql",
        path=Path(infra_base_path) / "5_sql",
        config={"namespace": zenml_namespace_name},
    )
    print("✅ MinIO and SQL deployed.")
    # Deploy orchestrator
    _ = deploy_stack(
        name="6_orchestrator",
        path=Path(infra_base_path) / "6_orchestrator",
        config={"namespace": zenml_namespace_name},
    )
    print("✅ Orchestrator deployed.")
    # Deploy persistent volume claims
    _ = deploy_stack(
        name="12_persistent_claims",
        path=Path(infra_base_path) / "12_persistent_claims",
        config={"namespace": zenml_namespace_name},
    )

    # Deploy monitoring components
    prometheus_stack = deploy_stack(
        name="13_prometheus", path=Path(infra_base_path) / "13_prometheus"
    )

    prometheus_stack_outputs = prometheus_stack.outputs()
    monitoring_namespace = prometheus_stack_outputs["monitoring_namespace"].value
    _ = deploy_stack(
        name="14_grafana",
        path=Path(infra_base_path) / "14_grafana",
        config={"monitoring_namespace": monitoring_namespace},
    )
    deploy_stack(
        name="16_additional_secrets",
        path=Path(infra_base_path) / "16_additional_secrets",
        config={"namespace": zenml_namespace_name},
    )
    print("Cleaning up downloaded charts...")
    charts_path = Path(infra_base_path) / "11_annotator/charts"
    zenml_charts_path = Path(infra_base_path) / "6_orchestrator/charts"
    if zenml_charts_path.exists():
        shutil.rmtree(str(zenml_charts_path))
        print("✅ ZenML charts cleaned up.")
    if charts_path.exists():
        shutil.rmtree(str(charts_path))
        print("✅ Charts cleaned up.")
