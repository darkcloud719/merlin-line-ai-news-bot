from __future__ import annotations

import json
from typing import Any

from azure.storage.blob import BlobServiceClient, ContentSettings
from pydantic import BaseModel


class BlobJsonRepository:
    def __init__(self, connection_string: str, container_name: str) -> None:
        service = BlobServiceClient.from_connection_string(connection_string)
        self._container_client = service.get_container_client(container_name)

    def load(self, blob_name: str) -> dict[str, Any]:
        blob_data = self._container_client.download_blob(blob_name).readall()
        return json.loads(blob_data)

    def save_model(self, blob_name: str, model: BaseModel) -> None:
        payload = model.model_dump_json(indent=2)
        self._container_client.upload_blob(
            name=blob_name,
            data=payload,
            overwrite=True,
            content_settings=ContentSettings(content_type="application/json; charset=utf-8"),
        )

