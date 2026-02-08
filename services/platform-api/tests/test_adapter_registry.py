import pytest

from adapters.loader import AdapterLoadError, load_object
from adapters.registry import AdapterRegistry
from config.models import PlatformConfig


def test_adapter_registry_loads_instance():
    config = PlatformConfig.model_validate(
        {
            "modules": {"module_catalog_path": "config/module_catalog.yaml"},
            "identity": {
                "oidc": {
                    "issuer_url": "https://issuer.example/realms/demo",
                    "audience": "platform-api",
                    "jwks_url": "https://issuer.example/realms/demo/protocol/openid-connect/certs",
                },
                "claims": {
                    "tenant_roles_claim": "tenant_roles",
                    "realm_roles_claim": "realm_access.roles",
                    "subject_claim": "sub",
                    "email_claim": "email",
                },
                "jwks_cache_seconds": 300,
            },
            "adapters": {
                "identity": "plugins.keycloak:KeycloakIdentityAdapter",
            },
            "rbac": {},
        }
    )
    registry = AdapterRegistry(config)
    identity = registry.identity()
    assert hasattr(identity, "verify_token")


def test_adapter_loader_invalid_path():
    with pytest.raises(AdapterLoadError):
        load_object("missing_colon")
