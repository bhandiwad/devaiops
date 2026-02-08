from __future__ import annotations

from uuid import uuid4

from artifacts.store import ArtifactRef, ArtifactStore


class S3ArtifactStore(ArtifactStore):
    def __init__(self, config: dict):
        self.bucket = config.get("bucket")
        if not self.bucket:
            raise RuntimeError("artifacts.bucket is required for s3 store")
        self.prefix = config.get("prefix", "")
        self.endpoint = config.get("endpoint")
        self.region = config.get("region")
        self.access_key = config.get("access_key")
        self.secret_key = config.get("secret_key")
        self._client = self._build_client()

    def _build_client(self):
        try:
            import boto3  # type: ignore
        except Exception as exc:
            raise RuntimeError("boto3 is required for S3ArtifactStore") from exc
        kwargs = {
            "service_name": "s3",
            "endpoint_url": self.endpoint,
            "region_name": self.region,
            "aws_access_key_id": self.access_key,
            "aws_secret_access_key": self.secret_key,
        }
        clean = {k: v for k, v in kwargs.items() if v}
        return boto3.client(**clean)

    def _key(self, artifact_id: str, name: str) -> str:
        base = f"{artifact_id}-{name}"
        if not self.prefix:
            return base
        return f"{self.prefix.rstrip('/')}/{base}"

    def put(self, name: str, data: bytes, content_type: str, tags: dict) -> ArtifactRef:
        artifact_id = str(uuid4())
        key = self._key(artifact_id, name)
        tagging = "&".join([f"{k}={v}" for k, v in (tags or {}).items()]) if tags else None
        kwargs = {
            "Bucket": self.bucket,
            "Key": key,
            "Body": data,
            "ContentType": content_type,
        }
        if tagging:
            kwargs["Tagging"] = tagging
        self._client.put_object(**kwargs)
        return ArtifactRef(artifact_id=artifact_id, location=f"s3://{self.bucket}/{key}")

    def get(self, artifact_ref: ArtifactRef) -> bytes:
        location = artifact_ref.location
        if not location.startswith("s3://"):
            raise RuntimeError(f"Invalid S3 artifact location: {location}")
        path = location[len("s3://") :]
        bucket, key = path.split("/", 1)
        obj = self._client.get_object(Bucket=bucket, Key=key)
        return obj["Body"].read()
