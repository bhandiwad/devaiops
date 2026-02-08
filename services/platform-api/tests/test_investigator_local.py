import httpx

from config.models import PlatformConfig
from plugins.investigator_local import LocalModelInvestigator


def test_local_investigator_fallback_to_rule_based():
    def handler(request: httpx.Request):
        return httpx.Response(200, json={"response": "not json"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    platform_config = PlatformConfig.model_validate(
        {
            "modules": {"module_catalog_path": "config/module_catalog.yaml"},
            "identity": {},
            "adapters": {},
            "rbac": {},
            "aiops": {
                "investigator_adapter": "plugins.investigator_local:LocalModelInvestigator",
                "allowlist_fix_types": ["ROLLBACK"],
                "max_prompt_chars": 1000,
                "local_model": {"base_url": "http://ollama", "model": "llama"},
            },
        }
    )
    adapter = LocalModelInvestigator(platform_config=platform_config, client=client)
    evidence = {"k8s": {"snapshot": []}}
    proposal = adapter.investigate(evidence)
    assert proposal["fix_type"]
