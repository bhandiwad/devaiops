from __future__ import annotations

from artifacts.store import ArtifactRef, ArtifactStore


class S3ArtifactStore(ArtifactStore):
    def __init__(self, config: dict):
        self.bucket = config.get("bucket")
        if not self.bucket:
            raise RuntimeError("artifacts.bucket is required for s3 store")
        self.prefix = config.get("prefix", "")
        self.endpoint = config.get("endpoint")

    def put(self, name: str, data: bytes, content_type: str, tags: dict) -> ArtifactRef:
        raise NotImplementedError("S3ArtifactStore.put not implemented")

    def get(self, artifact_ref: ArtifactRef) -> bytes:
        raise NotImplementedError("S3ArtifactStore.get not implemented")
