from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx
import yaml

from adapters.interfaces import (
    AppRef,
    AppStatus,
    ClusterAccess,
    ClusterRef,
    GitOpsAdapter,
    ProjectRef,
    SyncResult,
)


@dataclass
class ArgoCDConfig:
    server_url: str
    token: str
    verify_tls: bool = True


class ArgoCDGitOpsAdapter(GitOpsAdapter):
    """Argo CD GitOps adapter using the REST API."""

    def __init__(self, platform_config=None, client: Optional[httpx.Client] = None) -> None:
        self._config = self._load_config(platform_config)
        self._client = client or httpx.Client(
            base_url=self._config.server_url.rstrip("/"),
            verify=self._config.verify_tls,
            timeout=20.0,
        )

    def _load_config(self, platform_config) -> ArgoCDConfig:
        server_url = os.getenv("ARGOCD_SERVER")
        token = os.getenv("ARGOCD_TOKEN")
        verify_tls = True
        if platform_config:
            gitops = (platform_config.gitops or {}).get("argocd", {})
            server_url = server_url or gitops.get("server_url")
            verify_tls = gitops.get("verify_tls", True)
        if not server_url:
            raise RuntimeError("Argo CD server URL missing (ARGOCD_SERVER or PlatformConfig.gitops.argocd.server_url)")
        if not token:
            raise RuntimeError("Argo CD token missing (ARGOCD_TOKEN)")
        return ArgoCDConfig(server_url=server_url, token=token, verify_tls=verify_tls)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self._config.token}"}

    def _request(self, method: str, path: str, json_body: Dict[str, Any] | None = None) -> Dict[str, Any]:
        response = self._client.request(method, path, headers=self._headers(), json=json_body)
        if response.status_code >= 400:
            raise RuntimeError(f"Argo CD API error {response.status_code}: {response.text}")
        if response.content:
            return response.json()
        return {}

    def _parse_kubeconfig(self, kubeconfig: str) -> Dict[str, Any]:
        config = yaml.safe_load(kubeconfig)
        current_context = config.get("current-context")
        context = next(
            (ctx for ctx in config.get("contexts", []) if ctx.get("name") == current_context),
            None,
        )
        if not context:
            raise RuntimeError("kubeconfig missing current context")
        cluster_name = context["context"].get("cluster")
        user_name = context["context"].get("user")
        cluster = next(
            (c for c in config.get("clusters", []) if c.get("name") == cluster_name),
            None,
        )
        user = next((u for u in config.get("users", []) if u.get("name") == user_name), None)
        if not cluster:
            raise RuntimeError("kubeconfig missing cluster")
        if not user:
            raise RuntimeError("kubeconfig missing user")
        return {
            "server": cluster["cluster"].get("server"),
            "caData": cluster["cluster"].get("certificate-authority-data"),
            "insecure": cluster["cluster"].get("insecure-skip-tls-verify", False),
            "token": user["user"].get("token"),
            "clientCertData": user["user"].get("client-certificate-data"),
            "clientKeyData": user["user"].get("client-key-data"),
        }

    def register_cluster(self, tenant_id: str, cluster_access: ClusterAccess, rbac_policy: Dict[str, Any]) -> ClusterRef:
        if not cluster_access.kubeconfig:
            raise RuntimeError("ClusterAccess.kubeconfig required for Argo CD registration")
        kubeconfig = self._parse_kubeconfig(cluster_access.kubeconfig)
        payload = {
            "name": f"{tenant_id}-cluster",
            "server": kubeconfig["server"],
            "config": {
                "bearerToken": kubeconfig.get("token"),
                "tlsClientConfig": {
                    "insecure": kubeconfig.get("insecure", False),
                    "caData": kubeconfig.get("caData"),
                    "certData": kubeconfig.get("clientCertData"),
                    "keyData": kubeconfig.get("clientKeyData"),
                },
            },
            "labels": {"tenant_id": tenant_id},
        }
        self._request("POST", "/api/v1/clusters", json_body=payload)
        return ClusterRef(cluster_id=payload["name"], metadata={"server": payload["server"]})

    def ensure_tenant_project(self, tenant_id: str, project_policy: Dict[str, Any]) -> ProjectRef:
        name = project_policy.get("name") or tenant_id
        try:
            self._request("GET", f"/api/v1/projects/{name}")
            return ProjectRef(project_id=name)
        except RuntimeError:
            project_spec = {
                "metadata": {"name": name},
                "spec": {
                    "description": f"Tenant project {tenant_id}",
                    "sourceRepos": project_policy.get("source_repos", ["*"]),
                    "destinations": project_policy.get(
                        "destinations",
                        [{"namespace": "*", "server": project_policy.get("server", "*")}],
                    ),
                    "clusterResourceWhitelist": project_policy.get(
                        "cluster_resource_whitelist",
                        [{"group": "*", "kind": "*"}],
                    ),
                },
            }
            self._request("POST", "/api/v1/projects", json_body=project_spec)
            return ProjectRef(project_id=name)

    def apply_application(self, app_spec: Dict[str, Any]) -> AppRef:
        app_name = app_spec.get("metadata", {}).get("name") or app_spec.get("name")
        if not app_name:
            raise RuntimeError("app_spec must include metadata.name")
        payload = {"metadata": app_spec.get("metadata", {}), "spec": app_spec.get("spec", {})}
        try:
            self._request("GET", f"/api/v1/applications/{app_name}")
            self._request("PUT", f"/api/v1/applications/{app_name}", json_body=payload)
        except RuntimeError:
            self._request("POST", "/api/v1/applications", json_body=payload)
        return AppRef(app_id=app_name)

    def get_application_status(self, app_ref: AppRef) -> AppStatus:
        response = self._request("GET", f"/api/v1/applications/{app_ref.app_id}")
        return AppStatus(status=response.get("status", {}).get("health", {}).get("status", "unknown"), detail=response)

    def sync_application(self, app_ref: AppRef) -> SyncResult:
        response = self._request("POST", f"/api/v1/applications/{app_ref.app_id}/sync")
        return SyncResult(status="sync_started", detail=response)
