from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

from artifacts.store import ArtifactRef, ArtifactStore
from db.models import ArtifactRef as ArtifactRefModel
from db.repositories import ArtifactRefRepository


class ArtifactService:
    def __init__(self, store: ArtifactStore, repository: ArtifactRefRepository) -> None:
        self._store = store
        self._repo = repository

    async def put(
        self,
        tenant_id: Optional[str],
        name: str,
        data: bytes,
        content_type: str,
        tags: Dict[str, Any] | None = None,
    ) -> ArtifactRefModel:
        tags = tags or {}
        ref = self._store.put(name=name, data=data, content_type=content_type, tags=tags)
        model = ArtifactRefModel(
            artifact_id=ref.artifact_id or str(uuid4()),
            tenant_id=tenant_id,
            name=name,
            location=ref.location,
            content_type=content_type,
            tags=tags,
        )
        return await self._repo.create(model)

    async def get_bytes(self, artifact: ArtifactRefModel) -> bytes:
        ref = ArtifactRef(artifact_id=artifact.artifact_id, location=artifact.location)
        return self._store.get(ref)
