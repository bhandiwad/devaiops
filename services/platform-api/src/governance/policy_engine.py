from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import httpx
import yaml

from models.identity import PrincipalContext


@dataclass
class PolicyDecisionResult:
    allow: bool
    reasons: List[str]
    obligations: List[Dict[str, Any]]


@dataclass
class PolicyContext:
    action: str
    principal: PrincipalContext
    tenant_id: Optional[str]
    payload: Dict[str, Any]
    request_meta: Dict[str, Any]


class BasePolicyEngine(ABC):
    @abstractmethod
    def evaluate(self, context: PolicyContext) -> PolicyDecisionResult:
        pass


def _roles_for(principal: PrincipalContext, tenant_id: Optional[str]) -> List[str]:
    roles = list(principal.realm_roles)
    if tenant_id:
        roles.extend(principal.tenant_roles.get(tenant_id, []))
    return roles


def _risk_rank(level: str) -> int:
    mapping = {"low": 1, "medium": 2, "high": 3}
    return mapping.get(level.lower(), 999)


class SimplePolicyEngine(BasePolicyEngine):
    def __init__(self, rules: List[Dict[str, Any]], deny_by_default: bool = True) -> None:
        self._rules = rules
        self._deny_by_default = deny_by_default

    @classmethod
    def from_files(cls, files: Iterable[Path], deny_by_default: bool = True) -> "SimplePolicyEngine":
        rules: List[Dict[str, Any]] = []
        for file_path in files:
            if not file_path.exists():
                continue
            data = yaml.safe_load(file_path.read_text()) or {}
            rules.extend(data.get("policies", []))
        return cls(rules=rules, deny_by_default=deny_by_default)

    def _action_matches(self, rule_action: Any, action: str) -> bool:
        if isinstance(rule_action, list):
            return any(self._action_matches(item, action) for item in rule_action)
        if not isinstance(rule_action, str):
            return False
        if rule_action == "*" or rule_action == action:
            return True
        if rule_action.endswith("*"):
            return action.startswith(rule_action[:-1])
        return False

    def _check_conditions(self, conditions: Dict[str, Any], context: PolicyContext) -> List[str]:
        reasons: List[str] = []
        roles = _roles_for(context.principal, context.tenant_id)
        payload = context.payload

        if "roles_any" in conditions:
            allowed = set(conditions.get("roles_any") or [])
            if not any(role in allowed for role in roles):
                reasons.append("role_not_allowed")

        if "tenant_ids" in conditions:
            allowed = set(conditions.get("tenant_ids") or [])
            if context.tenant_id not in allowed:
                reasons.append("tenant_not_allowed")

        if "fix_types" in conditions:
            allowed = set(conditions.get("fix_types") or [])
            if payload.get("fix_type") not in allowed:
                reasons.append("fix_type_not_allowed")

        if "paths_allowlist" in conditions:
            allowlist = conditions.get("paths_allowlist") or []
            paths = payload.get("paths") or []
            for path in paths:
                if not any(path.startswith(prefix) for prefix in allowlist):
                    reasons.append(f"path_not_allowed:{path}")
                    break

        if "runbook_ids" in conditions:
            allowed = set(conditions.get("runbook_ids") or [])
            if payload.get("runbook_id") not in allowed:
                reasons.append("runbook_not_allowed")

        if "modules" in conditions:
            allowed = set(conditions.get("modules") or [])
            if payload.get("module_id") not in allowed:
                reasons.append("module_not_allowed")

        if "namespaces" in conditions:
            allowed = set(conditions.get("namespaces") or [])
            if payload.get("namespace") not in allowed:
                reasons.append("namespace_not_allowed")

        if "risk_max" in conditions:
            max_level = conditions.get("risk_max")
            if _risk_rank(payload.get("risk_level", "unknown")) > _risk_rank(str(max_level)):
                reasons.append("risk_too_high")

        if "required_checks" in conditions:
            required = set(conditions.get("required_checks") or [])
            checks = payload.get("checks") or []
            names_ok = {check.get("name") for check in checks if check.get("status") == "success"}
            if not required.issubset(names_ok):
                reasons.append("required_checks_missing")

        return reasons

    def evaluate(self, context: PolicyContext) -> PolicyDecisionResult:
        for rule in self._rules:
            if not self._action_matches(rule.get("action"), context.action):
                continue
            conditions = rule.get("conditions") or {}
            reasons = self._check_conditions(conditions, context)
            if reasons:
                continue
            obligations = list(rule.get("obligations") or [])
            if "required_checks" in conditions:
                obligations.append({"type": "required_checks", "checks": conditions.get("required_checks")})
            if rule.get("effect", "allow") == "deny":
                return PolicyDecisionResult(allow=False, reasons=[rule.get("reason", "policy_denied")], obligations=[])
            return PolicyDecisionResult(allow=True, reasons=[], obligations=obligations)
        if self._deny_by_default:
            return PolicyDecisionResult(allow=False, reasons=["no_matching_policy"], obligations=[])
        return PolicyDecisionResult(allow=True, reasons=[], obligations=[])


class OpaPolicyEngine(BasePolicyEngine):
    def __init__(self, opa_url: str, timeout: float = 5.0) -> None:
        self._client = httpx.Client(base_url=opa_url.rstrip("/"), timeout=timeout)

    def evaluate(self, context: PolicyContext) -> PolicyDecisionResult:
        payload = {
            "input": {
                "action": context.action,
                "tenant_id": context.tenant_id,
                "principal": context.principal.model_dump(),
                "payload": context.payload,
                "request": context.request_meta,
            }
        }
        response = self._client.post("/v1/data/aiops/policy", json=payload)
        if response.status_code >= 400:
            return PolicyDecisionResult(allow=False, reasons=["opa_error"], obligations=[])
        data = response.json().get("result") or {}
        allow = bool(data.get("allow", False))
        reasons = data.get("reasons") or []
        obligations = data.get("obligations") or []
        return PolicyDecisionResult(allow=allow, reasons=reasons, obligations=obligations)


def load_policy_engine(config: Dict[str, Any], repo_root: Path) -> BasePolicyEngine:
    policy_cfg = config.get("policy") or {}
    engine = policy_cfg.get("engine", "simple")
    deny_by_default = policy_cfg.get("deny_by_default", True)
    if engine == "opa":
        opa_url = policy_cfg.get("opa_url")
        if not opa_url:
            raise RuntimeError("policy.opa_url is required for OPA engine")
        return OpaPolicyEngine(opa_url=opa_url)

    rules_path = policy_cfg.get("rules_path", "config/policies")
    files = [Path(repo_root) / rules_path]
    rule_files: List[Path] = []
    for path in files:
        if path.is_dir():
            rule_files.extend(sorted(path.glob("*.y*ml")))
        elif path.exists():
            rule_files.append(path)
    return SimplePolicyEngine.from_files(rule_files, deny_by_default=deny_by_default)
