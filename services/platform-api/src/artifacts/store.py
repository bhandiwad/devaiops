from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict


@dataclass
class ArtifactRef:
    artifact_id: str
    location: str


class ArtifactStore(ABC):
    @abstractmethod
    def put(self, name: str, data: bytes, content_type: str, tags: Dict[str, str]) -> ArtifactRef:
        pass

    @abstractmethod
    def get(self, artifact_ref: ArtifactRef) -> bytes:
        pass
