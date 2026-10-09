from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    azure_openai_api_key: str
    azure_openai_api_version: str
    azure_openai_endpoint: str
    azure_openai_chat_deployment_name: str
    azure_storage_connection_string: str
    azure_storage_container_name: str
    channel_access_token: str
    channel_secret: str

    @classmethod
    def from_environment(cls) -> "Settings":
        names = {
            "azure_openai_api_key": "AZURE_OPENAI_API_KEY",
            "azure_openai_api_version": "AZURE_OPENAI_API_VERSION",
            "azure_openai_endpoint": "AZURE_OPENAI_ENDPOINT",
            "azure_openai_chat_deployment_name": "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME",
            "azure_storage_connection_string": "AZURE_STORAGE_CONNECTION_STRING",
            "azure_storage_container_name": "AZURE_STORAGE_CONTAINER_NAME",
            "channel_access_token": "CHANNEL_ACCESS_TOKEN",
            "channel_secret": "CHANNEL_SECRET",
        }
        values = {field: os.getenv(environment_name, "").strip() for field, environment_name in names.items()}
        missing = [names[field] for field, value in values.items() if not value]
        if missing:
            raise RuntimeError(f"Missing required settings: {', '.join(sorted(missing))}")
        return cls(**values)

