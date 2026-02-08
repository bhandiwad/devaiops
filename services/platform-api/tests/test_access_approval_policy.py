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
async def test_access_approval_two_person_rule():
    engine = SimplePolicyEngine(
        rules=[
            {
                "action": "access.request.approve",
                "effect": "allow",
                "obligations": [{"type": "require_2person_rule"}],
            }
        ],
        deny_by_default=False,
    )
    scope = {"type": "http", "method": "POST", "path": "/x", "headers": []}
    scope["app"] = types.SimpleNamespace(state=types.SimpleNamespace(governance_policy_engine=engine))
    request = Request(scope)
    request.state.correlation_id = "corr"
    principal = PrincipalContext(principal_id="admin1", realm_roles=["tenant_admin"], tenant_roles={"t1": ["tenant_admin"]})
    with pytest.raises(HTTPException):
        await evaluate_and_record_policy(
            request=request,
            principal=principal,
            action="access.request.approve",
            payload={"requested_role": "tenant_admin"},
            policy_service=StubPolicyService(),
            tenant_id="t1",
        )
