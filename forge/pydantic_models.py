"""Pydantic models for ZenML stack configuration."""

import os
from typing import Optional
from pydantic import BaseModel, model_validator


class ClientKwargs(BaseModel):
    """Client kwargs for S3-compatible storage."""

    endpoint_url: str
    region_name: str


class ArtifactStoreConfiguration(BaseModel):
    """Configuration for artifact store."""

    path: str
    client_kwargs: ClientKwargs


class ArtifactStore(BaseModel):
    """Artifact store component."""

    name: str
    flavor: str
    configuration: ArtifactStoreConfiguration


class OrchestratorConfiguration(BaseModel):
    """Configuration for orchestrator."""

    kubernetes_context: str


class Orchestrator(BaseModel):
    """Orchestrator component."""

    name: str
    flavor: str
    configuration: OrchestratorConfiguration


class ContainerRegistryConfiguration(BaseModel):
    """Configuration for container registry."""

    uri: str


class ContainerRegistry(BaseModel):
    """Container registry component."""

    name: str
    flavor: str
    configuration: ContainerRegistryConfiguration


class CodeRepositoryConfiguration(BaseModel):
    """Configuration for code repository."""

    owner: str
    repository: str
    token: Optional[str] = None


class CodeRepository(BaseModel):
    """Code repository component."""

    name: str
    flavor: str
    configuration: CodeRepositoryConfiguration


class AlerterConfiguration(BaseModel):
    """Configuration for alerter."""

    slack_token: Optional[str] = None
    channel_id: Optional[str] = None

    @model_validator(mode="after")
    def populate_from_env(self) -> "AlerterConfiguration":
        """Auto-populate slack_token and channel_id from environment variables if not set."""
        if self.slack_token is None:
            env_value = os.getenv("SLACK_TOKEN")
            if env_value:
                self.slack_token = env_value
        if self.channel_id is None:
            env_value = os.getenv("SLACK_CHANNEL_ID")
            if env_value:
                self.channel_id = env_value
        return self


class Alerter(BaseModel):
    """Alerter component."""

    name: str
    flavor: str
    configuration: AlerterConfiguration


class SecretValues(BaseModel):
    """Values for a secret."""

    pa_token: Optional[str] = None


class Secret(BaseModel):
    """Secret configuration."""

    env_var: str
    values: SecretValues

    @model_validator(mode="after")
    def populate_from_env(self) -> "Secret":
        """Auto-populate pa_token from environment variable if not set."""
        if self.values.pa_token is None:
            env_value = os.getenv(self.env_var)
            if env_value:
                self.values.pa_token = env_value
        return self


class Secrets(BaseModel):
    """All secrets configuration."""

    github_secret: Secret
    slack_secret: Secret


class StackComponents(BaseModel):
    """Stack component references."""

    orchestrator: str
    artifact_store: str
    container_registry: str
    alerter: str


class Stack(BaseModel):
    """Stack configuration."""

    name: str
    components: StackComponents


class ZenMLConfig(BaseModel):
    """Complete ZenML configuration."""

    artifact_store: ArtifactStore
    orchestrator: Orchestrator
    container_registry: ContainerRegistry
    code_repository: CodeRepository
    alerter: Alerter
    secrets: Secrets
    stack: Stack

    class Config:
        """Pydantic config."""

        validate_assignment = True
        extra = "forbid"
