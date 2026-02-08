from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, Request

from db.services import PolicyDecisionService
from governance.policy_engine import PolicyContext
from models.identity import PrincipalContext


def _extract_ticket_id(request: Request) -> Optional[str]:
    return request.headers.get("X-Ticket-Id")


def _extract_approval(request: Request) -> Optional[str]:
    return request.headers.get("X-Approved-By")


async def evaluate_and_record_policy(
    request: Request,
    principal: PrincipalContext,
    action: str,
    payload: Dict[str, Any],
    policy_service: PolicyDecisionService,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    engine = request.app.state.governance_policy_engine
    context = PolicyContext(
        action=action,
        principal=principal,
        tenant_id=tenant_id,
        payload=payload,
        request_meta={"path": request.url.path, "method": request.method},
    )
    decision = engine.evaluate(context)
    await policy_service.record(
        tenant_id=tenant_id,
        action=action,
        allow=decision.allow,
        reasons=decision.reasons,
        obligations=decision.obligations,
        principal=principal.model_dump(),
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    if not decision.allow:
        raise HTTPException(status_code=403, detail=f"Policy denied: {decision.reasons}")

    for obligation in decision.obligations:
        obligation_type = obligation.get("type") if isinstance(obligation, dict) else obligation
        if obligation_type == "require_ticket_id":
            if not _extract_ticket_id(request):
                raise HTTPException(status_code=403, detail="Policy requires ticket id")
        if obligation_type == "require_approval":
            if not _extract_approval(request):
                raise HTTPException(status_code=403, detail="Policy requires approval")
        if obligation_type == "require_2person_rule":
            approver = _extract_approval(request)
            if not approver or approver == principal.principal_id:
                raise HTTPException(status_code=403, detail="Policy requires two-person approval")
        if obligation_type == "require_signature_verification":
            if not payload.get("signature_verified"):
                raise HTTPException(status_code=403, detail="Policy requires signature verification")
    return {"allow": decision.allow, "obligations": decision.obligations}
