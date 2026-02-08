from __future__ import annotations

from adapters.interfaces import GitProviderAdapter, PRChecks, PRRef, PRStatus, RepoRef
from plugins.git_github import GitHubGitProviderAdapter


class GenericGitProviderAdapter(GitProviderAdapter):
    """Generic adapter that currently routes to the GitHub implementation."""

    def __init__(self, platform_config=None) -> None:
        self._delegate = GitHubGitProviderAdapter(platform_config=platform_config)

    def scaffold_repo(self, template_ref, parameters) -> RepoRef:
        return self._delegate.scaffold_repo(template_ref, parameters)

    def create_pull_request(self, repo_ref: RepoRef, branch: str, title: str, body: str, changes) -> PRRef:
        return self._delegate.create_pull_request(repo_ref, branch, title, body, changes)

    def get_pull_request_status(self, pr_ref: PRRef) -> PRStatus:
        return self._delegate.get_pull_request_status(pr_ref)

    def add_labels(self, pr_ref: PRRef, labels) -> None:
        self._delegate.add_labels(pr_ref, labels)

    def get_pull_request_checks(self, pr_ref: PRRef) -> PRChecks:
        return self._delegate.get_pull_request_checks(pr_ref)
