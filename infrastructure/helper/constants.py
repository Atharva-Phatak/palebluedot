from dataclasses import dataclass


@dataclass
class SecretToSecretName:
    github: str = "gha-rs-github-secret"
