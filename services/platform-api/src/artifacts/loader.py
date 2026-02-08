from __future__ import annotations

from artifacts.local import LocalFilesystemArtifactStore
from artifacts.s3 import S3ArtifactStore


def load_artifact_store(config: dict):
    artifacts_cfg = config.get("artifacts") or {}
    store_type = artifacts_cfg.get("store", "local")
    if store_type == "s3":
        return S3ArtifactStore(artifacts_cfg)
    base_path = artifacts_cfg.get("local_path", "/tmp/aiops-artifacts")
    return LocalFilesystemArtifactStore(base_path=base_path)
