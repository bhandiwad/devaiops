from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from artifacts.store import ArtifactRef, ArtifactStore


@dataclass
class LocalArtifactStoreConfig:
    base_path: Path


class LocalFilesystemArtifactStore(ArtifactStore):
    def __init__(self, base_path: str) -> None:
        self._config = LocalArtifactStoreConfig(base_path=Path(base_path))
        self._config.base_path.mkdir(parents=True, exist_ok=True)

    def put(self, name: str, data: bytes, content_type: str, tags: dict) -> ArtifactRef:
        artifact_id = str(uuid4())
        path = self._config.base_path / f"{artifact_id}-{name}"
        path.write_bytes(data)
        return ArtifactRef(artifact_id=artifact_id, location=str(path))

    def get(self, artifact_ref: ArtifactRef) -> bytes:
        return Path(artifact_ref.location).read_bytes()
