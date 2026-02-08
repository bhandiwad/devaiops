from __future__ import annotations

from adapters.interfaces import PRRef, RepoRef
from scaffolding.service import ScaffolderService


class StubGitProvider:
    def __init__(self) -> None:
        self.changes = []

    def scaffold_repo(self, template_ref, parameters):
        return RepoRef(repo_url="https://github.com/acme/demo", metadata={"default_branch": "main"})

    def create_pull_request(self, repo_ref, branch, title, body, changes):
        self.changes = changes
        return PRRef(pr_url="https://github.com/acme/demo/pull/1", metadata={"number": 1, "repo_url": repo_ref.repo_url})


class StubRegistry:
    def __init__(self) -> None:
        self.provider = StubGitProvider()

    def git_provider(self):
        return self.provider


def test_scaffold_generates_expected_files():
    registry = StubRegistry()
    service = ScaffolderService(registry)
    result = service.scaffold(
        tenant_id="tenant-a",
        template_id="python-fastapi",
        params={"service_name": "orders", "owner": "acme", "service_description": "Orders API"},
    )
    paths = {change["path"] for change in registry.provider.changes}
    assert "app/main.py" in paths
    assert "gitops/overlays/dev/kustomization.yaml" in paths
    assert result.repo_url == "https://github.com/acme/demo"
