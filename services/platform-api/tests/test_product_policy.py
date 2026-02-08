from governance.policy_engine import PolicyContext, SimplePolicyEngine
from models.identity import PrincipalContext


def test_product_enable_policy_requires_admin_role():
    engine = SimplePolicyEngine(
        rules=[
            {
                "action": "product.enable",
                "effect": "allow",
                "conditions": {"roles_any": ["tenant_admin", "platform_admin"]},
            }
        ],
        deny_by_default=True,
    )
    principal = PrincipalContext(principal_id="u1", realm_roles=["tenant_operator"], tenant_roles={"t1": ["tenant_operator"]})
    decision = engine.evaluate(
        PolicyContext(
            action="product.enable",
            principal=principal,
            tenant_id="t1",
            payload={"product_id": "observability.pack"},
            request_meta={},
        )
    )
    assert decision.allow is False
