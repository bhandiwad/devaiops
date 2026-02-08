from pathlib import Path

from aiops.redaction import redact_payload
from config.validator import SchemaValidator


def test_redaction_masks_tokens():
    payload = {"token": "abc", "nested": {"password": "secret"}, "value": "Bearer abc"}
    redacted, info = redact_payload(payload)
    assert redacted["token"] == "[REDACTED]"
    assert redacted["nested"]["password"] == "[REDACTED]"
    assert redacted["value"] == "[REDACTED]"
    assert info["redacted_fields"] >= 2


def test_evidence_schema_validation():
    repo_root = Path(__file__).resolve().parents[3]
    validator = SchemaValidator(repo_root / "schemas")
    evidence = {
        "incident_id": "inc-1",
        "tenant_id": "tenant-a",
        "alert": {"name": "test"},
        "k8s": {"events": [], "snapshot": []},
        "gitops": {},
        "metrics": {},
        "logs": {},
        "redaction": {"redacted_fields": 0},
    }
    validator.validate("evidence_pack.schema.json", evidence, repo_root / "schemas" / "evidence_pack.schema.json")
