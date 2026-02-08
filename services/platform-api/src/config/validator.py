from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator


@dataclass
class SchemaValidationError(Exception):
    message: str
    schema_name: str
    source_path: str
    errors: list[str]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.message} ({self.schema_name}) at {self.source_path}: {self.errors}"


class SchemaValidator:
    def __init__(self, schema_dir: Path) -> None:
        self._schema_dir = schema_dir

    def _load_schema(self, schema_name: str) -> dict[str, Any]:
        schema_path = self._schema_dir / schema_name
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")
        return json.loads(schema_path.read_text())

    def validate(self, schema_name: str, data: Any, source_path: Path) -> None:
        schema = self._load_schema(schema_name)
        validator = Draft7Validator(schema)
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            formatted: list[str] = []
            for err in errors:
                path = ".".join([str(p) for p in err.path]) or "<root>"
                formatted.append(f"{path}: {err.message}")
            raise SchemaValidationError(
                message="Schema validation failed",
                schema_name=schema_name,
                source_path=str(source_path),
                errors=formatted,
            )
