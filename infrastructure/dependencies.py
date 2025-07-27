# stack_dependencies maps a stack name to the stacks it depends on
stack_dependencies = {
    "1_cluster": [],
    "2_namespace": ["1_cluster"],
    "4_minio": ["2_namespace"],
    "5_postgres": ["2_namespace"],
    "6_orchestrator": ["5_postgres", "4_minio"],
    "7_arc_runner": ["1_cluster"],
    "8_argo_workflows": ["2_namespace", "6_orchestrator"],
    "9_argo_events": ["8_argo_workflows"],
    "10_webhooks": ["9_argo_events"],
    "11_annotator": ["1_cluster"],
    "12_persistent_claims": ["2_namespace"],
    "13_prometheus": [],
    "14_grafana": ["13_prometheus"],
}
