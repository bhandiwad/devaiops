from __future__ import annotations

import importlib
from dataclasses import dataclass


@dataclass
class AdapterLoadError(Exception):
    message: str

    def __str__(self) -> str:  # pragma: no cover
        return self.message


def load_object(import_path: str):
    if ":" not in import_path:
        raise AdapterLoadError(f"Invalid import path '{import_path}', expected 'module:attr'")
    module_name, attr_name = import_path.split(":", 1)
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise AdapterLoadError(f"Adapter module not found: {module_name}") from exc
    try:
        return getattr(module, attr_name)
    except AttributeError as exc:
        raise AdapterLoadError(f"Adapter attribute not found: {attr_name} in {module_name}") from exc
