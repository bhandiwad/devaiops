from __future__ import annotations

import types

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from governance.policy_engine import PolicyContext, SimplePolicyEngine
from governance.enforcement import evaluate_and_record_policy
from models.identity import PrincipalContext


class StubPolicyService:
    def __init__(self) -> None:
        self.records = []

    async def record(self, **kwargs):
        self.records.append(kwargs)


def _make_request(engine):
    scope = {"type": "http", "method": "POST", "path": "/", "headers": []}
    app = types.SimpleNamespace(state=types.SimpleNamespace(governance_policy_engine=engine))
    scope["app"] = app
    request = Request(scope)
    request.state.correlation_id = "corr-1"
    return request


def test_simple_policy_allows_role():
    engine = SimplePolicyEngine(
        rules=[
            {
                "action": "tenant.create",
                "effect": "allow",
                "conditions": {"roles_any": ["platform_admin"]},
            }
        ],
        deny_by_default=True,
    )
    principal = PrincipalContext(principal_id="user", realm_roles=["platform_admin"], tenant_roles={})
    context = PolicyContext(
        action="tenant.create",
        principal=principal,
        tenant_id=None,
        payload={},
        request_meta={},
    )
    decision = engine.evaluate(context)
    assert decision.allow is True


@pytest.mark.asyncio
async def test_policy_obligation_requires_ticket():
    engine = SimplePolicyEngine(
        rules=[
            {
                "action": "remediation.create_pr",
                "effect": "allow",
                "obligations": [{"type": "require_ticket_id"}],
            }
        ],
        deny_by_default=False,
    )
    request = _make_request(engine)
    principal = PrincipalContext(principal_id="user", realm_roles=["tenant_admin"], tenant_roles={"t1": ["tenant_admin"]})
    service = StubPolicyService()
    with pytest.raises(HTTPException):
        await evaluate_and_record_policy(
            request,
            principal,
            action="remediation.create_pr",
            tenant_id="t1",
            payload={},
            policy_service=service,
        )
