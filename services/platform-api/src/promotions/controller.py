from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from adapters.interfaces import RepoRef
from adapters.registry import AdapterRegistry


@dataclass
class PromotionResult:
    pr_url: str
    status: str


class PromotionController:
    def __init__(self, registry: AdapterRegistry) -> None:
        self._registry = registry

    def create_promotion_pr(
        self,
        repo_url: str,
        default_branch: str,
        service_id: str,
        from_env: str,
        to_env: str,
        image_tag: str,
        required_checks: list[str] | None = None,
    ) -> PromotionResult:
        path = f"gitops/overlays/{to_env}/{service_id}.yaml"
        content = (
            "apiVersion: v1\n"
            "kind: ConfigMap\n"
            f"metadata:\n  name: {service_id}-promotion\n"
            f"data:\n  promoted_from: {from_env}\n  image_tag: {image_tag}\n"
        )
        pr = self._registry.git_provider().create_pull_request(
            repo_ref=RepoRef(repo_url=repo_url, metadata={"default_branch": default_branch}),
            branch=f"promote/{service_id}/{from_env}-to-{to_env}",
            title=f"Promote {service_id}: {from_env} -> {to_env}",
            body=f"Promotion request for {service_id}",
            changes=[{"path": path, "content": content}],
        )
        status = "created"
        if required_checks:
            checks = self._registry.git_provider().get_pull_request_checks(pr)
            passed = {
                check.get("context") or check.get("name")
                for check in checks.checks
                if check.get("state") in ("success", "passed")
            }
            if not set(required_checks).issubset(passed):
                status = "pending_checks"
        return PromotionResult(pr_url=pr.pr_url, status=status)
