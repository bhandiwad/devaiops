from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


def _deep_merge(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


def merge_config_layers(
    platform_config: Mapping[str, Any],
    provider_profile: Mapping[str, Any] | None,
    tenant_spec: Mapping[str, Any] | None,
    env_overrides: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """
    Apply precedence rules:
    env_overrides > tenant_spec > provider_profile > platform_config.
    """
    merged = deepcopy(dict(platform_config))
    if provider_profile:
        merged = _deep_merge(merged, provider_profile)
    if tenant_spec:
        merged = _deep_merge(merged, tenant_spec)
    if env_overrides:
        merged = _deep_merge(merged, env_overrides)
    return merged
