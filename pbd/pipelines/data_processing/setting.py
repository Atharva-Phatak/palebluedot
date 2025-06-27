"""
Metaflow Kubernetes Configuration

This module provides configuration utilities for running Metaflow flows on Kubernetes.
It defines resource settings, Docker images, and Kubernetes-specific configurations
that mirror the ZenML settings structure.

Usage:
    from metaflow_k8s_config import get_k8s_decorator, DOCKER_IMAGE

    @get_k8s_decorator("processing")
    @step
    def my_step(self):
        pass
"""

from typing import Callable, Dict

from metaflow import kubernetes

# Docker image configuration
DOCKER_IMAGE = "ghcr.io/atharva-phatak/pbd-data_processing:latest"

# Resource configurations matching your ZenML settings
RESOURCE_CONFIGS = {
    "orchestrator": {
        "cpu": 1,
        "memory": 128,  # 256Mi in MB
        "secrets": ["aws-credentials"],
    },
    "discovery": {
        "cpu": 2,
        "memory": 1024,  # 1Gi in MB
        "secrets": ["aws-credentials"],
    },
    "processing": {
        "cpu": 4,
        "memory": 3072,  # 3Gi in MB
        "secrets": ["aws-credentials"],
    },
    "lightweight": {
        "cpu": 1,
        "memory": 512,  # 512Mi in MB
        "secrets": ["aws-credentials"],
    },
}


def get_k8s_decorator(
    config_type: str = "processing",
    docker_image: str = DOCKER_IMAGE,
    additional_labels: Dict[str, str] = None,
) -> Callable:
    """
    Get a Kubernetes decorator with specified resource configuration.

    Args:
        config_type: Type of resource configuration ('orchestrator', 'discovery', 'processing', 'lightweight')
        docker_image: Docker image to use
        additional_labels: Additional Kubernetes labels to apply

    Returns:
        Configured kubernetes decorator

    Raises:
        ValueError: If config_type is not recognized
    """
    if config_type not in RESOURCE_CONFIGS:
        raise ValueError(
            f"Unknown config_type: {config_type}. Must be one of {list(RESOURCE_CONFIGS.keys())}"
        )

    config = RESOURCE_CONFIGS[config_type].copy()

    return kubernetes(
        image=docker_image,
        cpu=config["cpu"],
        memory=config["memory"],
        secrets=config["secrets"],
    )


# Pre-configured decorators for common use cases
orchestrator_k8s = get_k8s_decorator("orchestrator")
discovery_k8s = get_k8s_decorator("discovery")
processing_k8s = get_k8s_decorator("processing")
lightweight_k8s = get_k8s_decorator("lightweight")
