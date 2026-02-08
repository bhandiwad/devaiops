from __future__ import annotations

from adapters.interfaces import PRChecks, PRRef
from promotions.controller import PromotionController


class StubGitProvider:
    def create_pull_request(self, repo_ref, branch, title, body, changes):
        return PRRef(pr_url="https://github.com/acme/demo/pull/2", metadata={"number": 2, "repo_url": repo_ref.repo_url})

    def get_pull_request_checks(self, pr_ref):
        return PRChecks(status="pending", checks=[{"context": "ci/lint", "state": "success"}])


class StubRegistry:
    def git_provider(self):
        return StubGitProvider()


def test_promotion_required_checks_gate():
    controller = PromotionController(StubRegistry())
    result = controller.create_promotion_pr(
        repo_url="https://github.com/acme/demo",
        default_branch="main",
        service_id="orders",
        from_env="stage",
        to_env="prod",
        image_tag="1.2.3",
        required_checks=["ci/lint", "ci/test"],
    )
    assert result.status == "pending_checks"
