from modules.engine import ModuleEngine


def test_module_engine_adapter_requirement_check():
    module_catalog = {
        "modules": [
            {
                "id": "obs.stack",
                "type": "INSTALL",
                "scope": "tenant",
                "requirements": {"adapters": ["observability"], "capabilities": {}, "optional": False},
                "install": {
                    "values_overrides": {},
                    "argo_application_template": {"metadata": {"name": "obs"}, "spec": {"source": {"helm": {}}}},
                },
            }
        ]
    }
    engine = ModuleEngine(module_catalog, platform_adapters={})
    tenant_spec = {"modules": {"enabled": ["obs.stack"]}}
    provider_profile = {"capabilities": {}}
    plan = engine.plan(tenant_spec, provider_profile, {"capabilities": {}})
    assert plan.errors
    assert "observability" in plan.errors[0]


def test_module_engine_capability_requirement_check():
    module_catalog = {
        "modules": [
            {
                "id": "obs.stack",
                "type": "INSTALL",
                "scope": "tenant",
                "requirements": {"adapters": [], "capabilities": {"supports_ingress": True}, "optional": False},
                "install": {
                    "values_overrides": {},
                    "argo_application_template": {"metadata": {"name": "obs"}, "spec": {"source": {"helm": {}}}},
                },
            }
        ]
    }
    engine = ModuleEngine(module_catalog, platform_adapters={"observability": "x"})
    tenant_spec = {"modules": {"enabled": ["obs.stack"]}}
    provider_profile = {"capabilities": {"supports_ingress": False}}
    plan = engine.plan(tenant_spec, provider_profile, {"capabilities": {}})
    assert plan.errors
    assert "supports_ingress" in plan.errors[0]
