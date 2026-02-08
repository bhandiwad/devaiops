from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
from dataclasses import field

import yaml

from config.merge import merge_config_layers
from config.models import ModuleCatalog, PlatformConfig, ProductDescriptor, ProviderProfile, TenantSpec
from config.validator import SchemaValidator


class ConfigError(Exception):
    pass


def find_repo_root(start: Path | None = None) -> Path:
    current = start or Path(__file__).resolve()
    for parent in [current, *current.parents]:
        if (parent / "schemas").exists() and (parent / "config").exists():
            return parent
    raise ConfigError("Unable to locate repository root (missing schemas/config)")


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if data is None:
        raise ConfigError(f"Config file is empty: {path}")
    return data


@dataclass
class ConfigStore:
    platform_config: PlatformConfig
    module_catalog: ModuleCatalog
    provider_profiles: Dict[str, ProviderProfile]
    tenant_specs: Dict[str, TenantSpec]
    products: Dict[str, ProductDescriptor] = field(default_factory=dict)

    def get_provider_profile(self, profile_id: str) -> ProviderProfile:
        if profile_id not in self.provider_profiles:
            raise ConfigError(f"ProviderProfile not found: {profile_id}")
        return self.provider_profiles[profile_id]

    def get_tenant_spec(self, tenant_id: str) -> TenantSpec:
        if tenant_id not in self.tenant_specs:
            raise ConfigError(f"TenantSpec not found: {tenant_id}")
        return self.tenant_specs[tenant_id]

    def get_effective_config(
        self,
        tenant_id: str,
        env_overrides: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        tenant_spec = self.get_tenant_spec(tenant_id)
        provider_profile = self.get_provider_profile(tenant_spec.provider_profile_id)
        return merge_config_layers(
            platform_config=self.platform_config.model_dump(),
            provider_profile=provider_profile.model_dump(),
            tenant_spec=tenant_spec.model_dump(),
            env_overrides=env_overrides,
        )

    def get_product(self, product_id: str) -> ProductDescriptor:
        if product_id not in self.products:
            raise ConfigError(f"ProductDescriptor not found: {product_id}")
        return self.products[product_id]


class ConfigLoader:
    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or find_repo_root()
        self.schema_validator = SchemaValidator(self.repo_root / "schemas")

    def load_platform_config(self, path: str | None = None) -> PlatformConfig:
        config_path = path or os.getenv("PLATFORM_CONFIG_PATH")
        if config_path is None:
            config_path = str(self.repo_root / "config" / "examples" / "platform_config.yaml")
        config_file = Path(config_path)
        data = _load_yaml(config_file)
        self.schema_validator.validate(
            "platform_config.schema.json", data, config_file
        )
        return PlatformConfig.model_validate(data)

    def load_module_catalog(self, platform_config: PlatformConfig) -> ModuleCatalog:
        module_path = platform_config.modules.get("module_catalog_path")
        if not module_path:
            raise ConfigError("PlatformConfig.modules.module_catalog_path is required")
        module_file = (self.repo_root / module_path).resolve()
        data = _load_yaml(module_file)
        if "modules" not in data or not isinstance(data["modules"], list):
            raise ConfigError("Module catalog must contain a 'modules' list")
        for idx, module in enumerate(data["modules"]):
            self.schema_validator.validate(
                "module_descriptor.schema.json", module, module_file
            )
            if not module.get("id"):
                raise ConfigError(f"Module entry {idx} missing id")
        return ModuleCatalog.model_validate(data)

    def _load_directory(self, directory: Path) -> List[Path]:
        if not directory.exists():
            raise ConfigError(f"Config directory not found: {directory}")
        files = [
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix in {".yaml", ".yml"}
        ]
        return sorted(files)

    def load_provider_profiles(self, platform_config: PlatformConfig) -> Dict[str, ProviderProfile]:
        if not platform_config.config_sources:
            raise ConfigError("PlatformConfig.config_sources is required")
        profiles_dir = (self.repo_root / platform_config.config_sources.provider_profiles_path).resolve()
        profiles: Dict[str, ProviderProfile] = {}
        for path in self._load_directory(profiles_dir):
            data = _load_yaml(path)
            if "tenant_id" in data:
                continue
            if "id" not in data or "capabilities" not in data:
                continue
            self.schema_validator.validate(
                "provider_profile.schema.json", data, path
            )
            profile = ProviderProfile.model_validate(data)
            profiles[profile.id] = profile
        return profiles

    def load_tenant_specs(self, platform_config: PlatformConfig) -> Dict[str, TenantSpec]:
        if not platform_config.config_sources:
            raise ConfigError("PlatformConfig.config_sources is required")
        tenants_dir = (self.repo_root / platform_config.config_sources.tenant_specs_path).resolve()
        tenants: Dict[str, TenantSpec] = {}
        for path in self._load_directory(tenants_dir):
            data = _load_yaml(path)
            if "tenant_id" not in data:
                continue
            self.schema_validator.validate("tenant_spec.schema.json", data, path)
            tenant = TenantSpec.model_validate(data)
            tenants[tenant.tenant_id] = tenant
        return tenants

    def load_all(self, path: str | None = None) -> ConfigStore:
        platform_config = self.load_platform_config(path)
        module_catalog = self.load_module_catalog(platform_config)
        provider_profiles = self.load_provider_profiles(platform_config)
        tenant_specs = self.load_tenant_specs(platform_config)
        products = self.load_products(platform_config)
        return ConfigStore(
            platform_config=platform_config,
            module_catalog=module_catalog,
            provider_profiles=provider_profiles,
            tenant_specs=tenant_specs,
            products=products,
        )

    def load_products(self, platform_config: PlatformConfig) -> Dict[str, ProductDescriptor]:
        products: Dict[str, ProductDescriptor] = {}
        if not platform_config.config_sources or not platform_config.config_sources.products_path:
            return products
        products_dir = (self.repo_root / platform_config.config_sources.products_path).resolve()
        for path in self._load_directory(products_dir):
            data = _load_yaml(path)
            if "required_modules" not in data or "name" not in data:
                continue
            self.schema_validator.validate("product_descriptor.schema.json", data, path)
            product = ProductDescriptor.model_validate(data)
            products[product.id] = product
        return products
