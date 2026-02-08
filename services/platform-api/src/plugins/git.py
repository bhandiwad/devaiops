from __future__ import annotations

from adapters.interfaces import GitProviderAdapter, PRChecks, PRRef, PRStatus, RepoRef


class GenericGitProviderAdapter(GitProviderAdapter):
    """Stub git provider adapter."""

    def scaffold_repo(self, template_ref, parameters) -> RepoRef:
        raise NotImplementedError("GenericGitProviderAdapter.scaffold_repo is not implemented")

    def create_pull_request(self, repo_ref: RepoRef, branch: str, title: str, body: str, changes) -> PRRef:
        raise NotImplementedError("GenericGitProviderAdapter.create_pull_request is not implemented")

    def get_pull_request_status(self, pr_ref: PRRef) -> PRStatus:
        raise NotImplementedError("GenericGitProviderAdapter.get_pull_request_status is not implemented")

    def add_labels(self, pr_ref: PRRef, labels) -> None:
        raise NotImplementedError("GenericGitProviderAdapter.add_labels is not implemented")

    def get_pull_request_checks(self, pr_ref: PRRef) -> PRChecks:
        raise NotImplementedError("GenericGitProviderAdapter.get_pull_request_checks is not implemented")
