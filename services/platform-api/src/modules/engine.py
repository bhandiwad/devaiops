from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
import yaml
from typing import Any, Dict, List, Optional


@dataclass
class ModulePlanItem:
    module_id: str
    module_type: str
    action: str
    app_spec: Optional[Dict[str, Any]] = None
    integration_ref: Optional[Dict[str, Any]] = None
    errors: List[str] = field(default_factory=list)


@dataclass
class ModulePlan:
    items: List[ModulePlanItem]
    errors: List[str]


class ModuleEngine:
    def __init__(self, module_catalog: Dict[str, Any], platform_adapters: Dict[str, Any]) -> None:
        self.module_catalog = module_catalog
        self.platform_adapters = platform_adapters

    def _get_enabled_modules(self, tenant_spec: Dict[str, Any]) -> List[str]:
        modules_cfg = tenant_spec.get("modules") or {}
        enabled = modules_cfg.get("enabled")
        if enabled:
            return list(enabled)
        enabled_required = []
        for module in self.module_catalog.get("modules", []):
            required = not module.get("requirements", {}).get("optional", False)
            if required:
                enabled_required.append(module.get("id"))
        return enabled_required

    def _merge_overrides(
        self,
        base: Dict[str, Any],
        provider_overrides: Dict[str, Any],
        tenant_overrides: Dict[str, Any],
    ) -> Dict[str, Any]:
        merged = dict(base)
        merged.update(provider_overrides)
        merged.update(tenant_overrides)
        return merged

    def _capabilities_match(self, required: Dict[str, Any], available: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        for key, expected in required.items():
            actual = available.get(key)
            if actual != expected:
                errors.append(f"Capability '{key}' required={expected} actual={actual}")
        return errors

    def _apply_placeholders(self, obj: Any, replacements: Dict[str, str]) -> Any:
        if isinstance(obj, dict):
            return {k: self._apply_placeholders(v, replacements) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._apply_placeholders(v, replacements) for v in obj]
        if isinstance(obj, str):
            value = obj
            for key, repl in replacements.items():
                value = value.replace(f"{{{{{key}}}}}", repl)
            return value
        return obj

    def plan(
        self,
        tenant_spec: Dict[str, Any],
        provider_profile: Dict[str, Any],
        capability_report: Dict[str, Any],
        tenant_id: str | None = None,
    ) -> ModulePlan:
        enabled_modules = set(self._get_enabled_modules(tenant_spec))
        provider_overrides = provider_profile.get("module_overrides") or {}
        tenant_overrides = (tenant_spec.get("modules") or {}).get("overrides") or {}

        items: List[ModulePlanItem] = []
        errors: List[str] = []

        capability_union = dict(provider_profile.get("capabilities", {}))
        capability_union.update(capability_report.get("capabilities", {}))

        for module in self.module_catalog.get("modules", []):
            module_id = module.get("id")
            if module_id not in enabled_modules:
                continue

            module_errors: List[str] = []
            requirements = module.get("requirements", {})
            adapter_requirements = requirements.get("adapters", []) or []
            for adapter_key in adapter_requirements:
                if adapter_key not in self.platform_adapters:
                    module_errors.append(f"Adapter '{adapter_key}' not configured")

            capability_requirements = requirements.get("capabilities", {}) or {}
            module_errors.extend(self._capabilities_match(capability_requirements, capability_union))

            if module_errors:
                errors.extend([f"{module_id}: {err}" for err in module_errors])
                items.append(
                    ModulePlanItem(
                        module_id=module_id,
                        module_type=module.get("type"),
                        action="error",
                        errors=module_errors,
                    )
                )
                continue

            if module.get("type") == "INSTALL":
                install_spec = module.get("install", {}) or {}
                base_values = install_spec.get("values_overrides", {}) or {}
                merged_values = self._merge_overrides(
                    base_values,
                    provider_overrides.get(module_id, {}),
                    tenant_overrides.get(module_id, {}),
                )
                template = install_spec.get("argo_application_template")
                if not template:
                    module_errors.append("argo_application_template is required for INSTALL modules")
                    errors.extend([f"{module_id}: {err}" for err in module_errors])
                    items.append(
                        ModulePlanItem(
                            module_id=module_id,
                            module_type=module.get("type"),
                            action="error",
                            errors=module_errors,
                        )
                    )
                    continue
                replacements = {
                    "tenant_id": tenant_id or tenant_spec.get("tenant_id", ""),
                    "tenant_repo_url": tenant_spec.get("git", {}).get("repo_url", ""),
                    "tenant_default_branch": tenant_spec.get("git", {}).get("default_branch", ""),
                }
                app_spec = self._apply_placeholders(deepcopy(template), replacements)
                metadata = app_spec.setdefault("metadata", {})
                if not metadata.get("name"):
                    metadata["name"] = f"{replacements['tenant_id']}-{module_id}"
                spec = app_spec.setdefault("spec", {})
                source = spec.get("source", {})
                if source.get("helm") is not None and merged_values:
                    source["helm"]["values"] = yaml.safe_dump(merged_values)
                    spec["source"] = source
                app_spec["spec"] = spec
                items.append(
                    ModulePlanItem(
                        module_id=module_id,
                        module_type=module.get("type"),
                        action="install",
                        app_spec=app_spec,
                        errors=[],
                    )
                )
            elif module.get("type") == "INTEGRATE":
                integrate_spec = module.get("integrate", {}) or {}
                adapter_config_requirements = integrate_spec.get("adapter_config_requirements", {}) or {}
                missing_configs = [
                    key for key in adapter_config_requirements.keys() if key not in self.platform_adapters
                ]
                if missing_configs:
                    module_errors = [f"Adapter config '{key}' missing" for key in missing_configs]
                    errors.extend([f"{module_id}: {err}" for err in module_errors])
                    items.append(
                        ModulePlanItem(
                            module_id=module_id,
                            module_type=module.get("type"),
                            action="error",
                            errors=module_errors,
                        )
                        )
                else:
                    items.append(
                        ModulePlanItem(
                            module_id=module_id,
                            module_type=module.get("type"),
                            action="integrate",
                            integration_ref={"module_id": module_id, "status": "validated"},
                            errors=[],
                        )
                    )
            elif module.get("type") == "SUPPLYCHAIN":
                supply_spec = module.get("supplychain", {}) or {}
                items.append(
                    ModulePlanItem(
                        module_id=module_id,
                        module_type=module.get("type"),
                        action="supplychain",
                        integration_ref={"tool": supply_spec.get("tool"), "options": supply_spec.get("options", {})},
                        errors=[],
                    )
                )
            else:
                errors.append(f"{module_id}: Unknown module type {module.get('type')}")

        return ModulePlan(items=items, errors=errors)
