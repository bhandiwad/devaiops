from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from adapters.registry import AdapterRegistry
from adapters.interfaces import RepoRef
from config.loader import ConfigStore


@dataclass
class PRCreationResult:
    pr_url: str
    pr_number: int | None
    status: str


def _approval_allows(risk_level: str, approval_policy: Dict[str, Any]) -> bool:
    policy = approval_policy.get(risk_level, "manual")
    return policy == "auto"


def _build_remediation_markdown(tenant_id: str, incident_id: str, proposal: Dict[str, Any]) -> str:
    lines: List[str] = [
        f"# Remediation Proposal for {tenant_id}/{incident_id}",
        "",
        f"Fix type: {proposal.get('fix_type')}",
        f"Risk level: {proposal.get('risk_level')}",
        "",
        f"Summary: {proposal.get('summary')}",
        f"Likely root cause: {proposal.get('likely_root_cause')}",
        "",
        f"Rollback plan: {proposal.get('rollback_plan')}",
        "",
        "Validation steps:",
    ]
    lines.extend([f"- {step}" for step in proposal.get("validation_steps", [])])
    lines.extend(["", "Evidence refs:"])
    lines.extend([f"- {ref}" for ref in proposal.get("evidence_refs", [])])
    return "\n".join(lines)


def create_remediation_pr(
    tenant_id: str,
    incident_id: str,
    proposal: Dict[str, Any],
    config_store: ConfigStore,
    registry: AdapterRegistry,
    required_checks: List[str] | None = None,
) -> PRCreationResult:
    tenant_spec = config_store.get_tenant_spec(tenant_id).model_dump()
    allowlist = tenant_spec.get("remediation_allowlist") or []
    if proposal.get("fix_type") not in allowlist:
        raise RuntimeError("Fix type not in remediation allowlist")

    approval_policy = tenant_spec.get("approval_policy") or {}
    if not _approval_allows(proposal.get("risk_level"), approval_policy):
        raise RuntimeError("Risk level requires manual approval")

    repo_url = tenant_spec.get("git", {}).get("repo_url")
    default_branch = tenant_spec.get("git", {}).get("default_branch")
    if not repo_url or not default_branch:
        raise RuntimeError("TenantSpec.git.repo_url and default_branch are required")

    body = _build_remediation_markdown(tenant_id, incident_id, proposal)
    file_path = f"remediations/incident-{incident_id}.md"

    pr_adapter = registry.git_provider()
    pr_ref = pr_adapter.create_pull_request(
        repo_ref=RepoRef(repo_url=repo_url, metadata={"default_branch": default_branch}),
        branch=f"aiops/{incident_id}",
        title=f"Remediation for {tenant_id}/{incident_id}",
        body=body,
        changes=[{"path": file_path, "content": body}],
    )

    labels = [
        f"tenant:{tenant_id}",
        f"incident:{incident_id}",
        f"fix_type:{proposal.get('fix_type')}",
        f"risk:{proposal.get('risk_level')}",
    ]
    pr_adapter.add_labels(pr_ref, labels)
    status = "created"
    if required_checks:
        checks = pr_adapter.get_pull_request_checks(pr_ref)
        passed = {check.get("context") or check.get("name") for check in checks.checks if check.get("state") in ("success", "passed")}
        if not set(required_checks).issubset(passed):
            status = "pending_checks"
    return PRCreationResult(
        pr_url=pr_ref.pr_url,
        pr_number=pr_ref.metadata.get("number"),
        status=status,
    )
