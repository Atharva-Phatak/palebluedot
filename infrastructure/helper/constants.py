from dataclasses import dataclass
from enum import StrEnum, auto


@dataclass
class SecretToSecretName:
    github: str = "gha-rs-github-secret"


class SecretNames(StrEnum):
    def _generate_next_value_(name, start, count, last_values):
        # Automatically use the lowercase member name as the value
        return name.lower()

    MINIO_ACCESS_KEY = auto()
    MINIO_SECRET_KEY = auto()
    MYSQL_PASSWORD = auto()
