from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class ArtifactRef:
    artifact_id: str
    location: str


class ArtifactStore:
    def put(self, name: str, data: bytes, content_type: str, tags: Dict[str, str]) -> ArtifactRef:
        raise NotImplementedError

    def get(self, artifact_ref: ArtifactRef) -> bytes:
        raise NotImplementedError
