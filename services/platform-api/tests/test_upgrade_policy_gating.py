from __future__ import annotations

import types

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from governance.enforcement import evaluate_and_record_policy
from governance.policy_engine import SimplePolicyEngine
from models.identity import PrincipalContext


class StubPolicyService:
    async def record(self, **kwargs):
        return kwargs


@pytest.mark.asyncio
async def test_upgrade_policy_requires_second_approver():
    engine = SimplePolicyEngine(
        rules=[
            {
                "action": "platform.upgrade.apply",
                "effect": "allow",
                "obligations": [{"type": "require_2person_rule"}],
            }
        ],
        deny_by_default=False,
    )
    scope = {"type": "http", "method": "POST", "path": "/platform/upgrade/apply", "headers": []}
    scope["app"] = types.SimpleNamespace(state=types.SimpleNamespace(governance_policy_engine=engine))
    request = Request(scope)
    request.state.correlation_id = "corr-upgrade"
    principal = PrincipalContext(principal_id="admin1", realm_roles=["platform_admin"], tenant_roles={})

    with pytest.raises(HTTPException):
        await evaluate_and_record_policy(
            request=request,
            principal=principal,
            action="platform.upgrade.apply",
            payload={"target_version": "0.8.0"},
            policy_service=StubPolicyService(),
            tenant_id=None,
        )
