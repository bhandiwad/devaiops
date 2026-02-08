from __future__ import annotations

import base64
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx

from adapters.interfaces import GitProviderAdapter, PRChecks, PRRef, PRStatus, RepoRef


@dataclass
class GitHubConfig:
    api_url: str
    token: str


class GitHubGitProviderAdapter(GitProviderAdapter):
    """GitHub implementation of GitProviderAdapter using REST API."""

    def __init__(self, platform_config=None, client: Optional[httpx.Client] = None) -> None:
        self._config = self._load_config(platform_config)
        self._client = client or httpx.Client(base_url=self._config.api_url.rstrip("/"), timeout=20.0)

    def _load_config(self, platform_config) -> GitHubConfig:
        api_url = "https://api.github.com"
        if platform_config:
            git_provider = (platform_config.git_provider or {})
            api_url = git_provider.get("api_url", api_url)
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise RuntimeError("GITHUB_TOKEN is required for GitHub adapter")
        return GitHubConfig(api_url=api_url, token=token)

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._config.token}",
            "Accept": "application/vnd.github+json",
        }

    def _request(self, method: str, path: str, json_body: Dict[str, Any] | None = None) -> Dict[str, Any]:
        response = self._client.request(method, path, headers=self._headers(), json=json_body)
        if response.status_code >= 400:
            raise RuntimeError(f"GitHub API error {response.status_code}: {response.text}")
        if response.content:
            return response.json()
        return {}

    def _parse_repo(self, repo_url: str) -> Tuple[str, str]:
        patterns = [
            r"git@github.com:(?P<owner>[^/]+)/(?P<repo>[^.]+)",
            r"https://github.com/(?P<owner>[^/]+)/(?P<repo>[^.]+)",
            r"https://github.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/?",
        ]
        for pattern in patterns:
            match = re.match(pattern, repo_url)
            if match:
                return match.group("owner"), match.group("repo")
        raise RuntimeError(f"Unsupported GitHub repo URL: {repo_url}")

    def _get_branch_ref(self, owner: str, repo: str, branch: str) -> Dict[str, Any]:
        return self._request("GET", f"/repos/{owner}/{repo}/git/refs/heads/{branch}")

    def _get_commit(self, owner: str, repo: str, sha: str) -> Dict[str, Any]:
        return self._request("GET", f"/repos/{owner}/{repo}/git/commits/{sha}")

    def _create_blob(self, owner: str, repo: str, content: str) -> str:
        body = {
            "content": base64.b64encode(content.encode("utf-8")).decode("utf-8"),
            "encoding": "base64",
        }
        response = self._request("POST", f"/repos/{owner}/{repo}/git/blobs", json_body=body)
        return response["sha"]

    def _create_tree(self, owner: str, repo: str, base_tree: str, changes: List[Dict[str, Any]]) -> str:
        tree = []
        for change in changes:
            blob_sha = self._create_blob(owner, repo, change["content"])
            tree.append(
                {
                    "path": change["path"],
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_sha,
                }
            )
        response = self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/trees",
            json_body={"base_tree": base_tree, "tree": tree},
        )
        return response["sha"]

    def _create_commit(self, owner: str, repo: str, message: str, tree_sha: str, parent_sha: str) -> str:
        response = self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/commits",
            json_body={"message": message, "tree": tree_sha, "parents": [parent_sha]},
        )
        return response["sha"]

    def _create_branch(self, owner: str, repo: str, branch: str, sha: str) -> None:
        self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/refs",
            json_body={"ref": f"refs/heads/{branch}", "sha": sha},
        )

    def scaffold_repo(self, template_ref: Dict[str, Any], parameters: Dict[str, Any]) -> RepoRef:
        owner = parameters.get("owner")
        repo_name = parameters.get("repo_name")
        private = bool(parameters.get("private", True))
        description = parameters.get("description", "Provisioned by AIOps Platform")
        default_branch = parameters.get("default_branch", "main")
        if not repo_name:
            raise RuntimeError("repo_name is required for scaffold_repo")
        body = {
            "name": repo_name,
            "private": private,
            "description": description,
            "auto_init": True,
        }
        if owner:
            repo = self._request("POST", f"/orgs/{owner}/repos", json_body=body)
        else:
            repo = self._request("POST", "/user/repos", json_body=body)
        return RepoRef(
            repo_url=repo["html_url"],
            metadata={
                "default_branch": default_branch,
                "full_name": repo.get("full_name"),
                "clone_url": repo.get("clone_url"),
            },
        )

    def create_pull_request(
        self, repo_ref: RepoRef, branch: str, title: str, body: str, changes: List[Dict[str, Any]]
    ) -> PRRef:
        owner, repo = self._parse_repo(repo_ref.repo_url)
        default_branch = repo_ref.metadata.get("default_branch")
        if not default_branch:
            raise RuntimeError("default_branch is required in RepoRef.metadata")

        base_ref = self._get_branch_ref(owner, repo, default_branch)
        base_sha = base_ref["object"]["sha"]
        base_commit = self._get_commit(owner, repo, base_sha)
        base_tree_sha = base_commit["tree"]["sha"]

        tree_sha = self._create_tree(owner, repo, base_tree_sha, changes)
        commit_sha = self._create_commit(owner, repo, title, tree_sha, base_sha)
        self._create_branch(owner, repo, branch, commit_sha)

        pr = self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls",
            json_body={"title": title, "head": branch, "base": default_branch, "body": body},
        )
        return PRRef(
            pr_url=pr["html_url"],
            metadata={"number": pr["number"], "sha": commit_sha, "repo_url": repo_ref.repo_url},
        )

    def get_pull_request_status(self, pr_ref: PRRef) -> PRStatus:
        pr_number = pr_ref.metadata.get("number")
        if not pr_number:
            raise RuntimeError("PR number required in PRRef.metadata")
        owner, repo = self._parse_repo(pr_ref.metadata.get("repo_url", pr_ref.pr_url))
        pr = self._request("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}")
        status = pr.get("state")
        detail = pr
        sha = pr.get("head", {}).get("sha")
        if sha:
            checks = self._request("GET", f"/repos/{owner}/{repo}/commits/{sha}/status")
            detail = {"pr": pr, "checks": checks}
        return PRStatus(status=status or "unknown", detail=detail)

    def add_labels(self, pr_ref: PRRef, labels: List[str]) -> None:
        pr_number = pr_ref.metadata.get("number")
        if not pr_number:
            raise RuntimeError("PR number required in PRRef.metadata")
        owner, repo = self._parse_repo(pr_ref.metadata.get("repo_url", pr_ref.pr_url))
        self._request("POST", f"/repos/{owner}/{repo}/issues/{pr_number}/labels", json_body={"labels": labels})

    def get_pull_request_checks(self, pr_ref: PRRef) -> PRChecks:
        pr_number = pr_ref.metadata.get("number")
        if not pr_number:
            raise RuntimeError("PR number required in PRRef.metadata")
        owner, repo = self._parse_repo(pr_ref.metadata.get("repo_url", pr_ref.pr_url))
        pr = self._request("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}")
        sha = pr.get("head", {}).get("sha")
        if not sha:
            return PRChecks(status="unknown", checks=[])
        checks = self._request("GET", f"/repos/{owner}/{repo}/commits/{sha}/status")
        status = checks.get("state", "unknown")
        return PRChecks(status=status, checks=checks.get("statuses", []))
