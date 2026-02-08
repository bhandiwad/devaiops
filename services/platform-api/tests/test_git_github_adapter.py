import json

import httpx
import pytest

from adapters.interfaces import RepoRef
from plugins.git_github import GitHubGitProviderAdapter


def test_github_create_pr(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    calls = []

    def handler(request: httpx.Request):
        calls.append((request.method, request.url.path, request.content))
        if request.url.path.endswith("/git/refs/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "base"}})
        if request.url.path.endswith("/git/commits/base"):
            return httpx.Response(200, json={"tree": {"sha": "tree"}})
        if request.url.path.endswith("/git/blobs"):
            return httpx.Response(200, json={"sha": "blob"})
        if request.url.path.endswith("/git/trees"):
            return httpx.Response(200, json={"sha": "newtree"})
        if request.url.path.endswith("/git/commits"):
            return httpx.Response(200, json={"sha": "newcommit"})
        if request.url.path.endswith("/git/refs"):
            return httpx.Response(201, json={"ref": "refs/heads/branch"})
        if request.url.path.endswith("/pulls"):
            return httpx.Response(201, json={"html_url": "https://github.com/org/repo/pull/1", "number": 1})
        return httpx.Response(200, json={})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://api.github.com")
    adapter = GitHubGitProviderAdapter(platform_config=None, client=client)
    pr = adapter.create_pull_request(
        RepoRef(repo_url="https://github.com/org/repo", metadata={"default_branch": "main"}),
        branch="aiops/test",
        title="Fix",
        body="Body",
        changes=[{"path": "README.md", "content": "hello"}],
    )
    assert pr.pr_url.endswith("/pull/1")
