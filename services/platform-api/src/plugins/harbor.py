from __future__ import annotations

import os
from typing import Any, Dict

import httpx

from adapters.interfaces import ProjectRef, RegistryAdapter, RobotCredentials


ROLE_MAP = {
    "projectadmin": 1,
    "maintainer": 2,
    "developer": 3,
    "guest": 4,
    "limitedguest": 5,
}


class HarborRegistryAdapter(RegistryAdapter):
    """Harbor registry adapter backed by Harbor v2 API."""

    def __init__(self, platform_config=None) -> None:
        cfg = (platform_config.registry or {}).get("harbor", {}) if platform_config else {}
        self._base_url = str(cfg.get("base_url") or os.getenv("HARBOR_BASE_URL") or "http://harbor.registry.svc.cluster.local").rstrip("/")
        self._project_prefix = str(cfg.get("project_prefix") or "tenant-")
        self._username = str(os.getenv("HARBOR_ADMIN_USERNAME", "admin"))
        self._password = os.getenv("HARBOR_ADMIN_PASSWORD")
        if not self._password:
            raise RuntimeError("HARBOR_ADMIN_PASSWORD is required")
        timeout_seconds = float((platform_config.integrations or {}).get("timeout_seconds", 10)) if platform_config else 10.0
        self._timeout = timeout_seconds

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self._base_url,
            auth=(self._username, self._password),
            timeout=self._timeout,
        )

    def _project_name(self, tenant_id: str, project_spec: Dict[str, Any] | None = None) -> str:
        if project_spec and project_spec.get("project_name"):
            return str(project_spec["project_name"])
        if project_spec and project_spec.get("name"):
            return str(project_spec["name"])
        return f"{self._project_prefix}{tenant_id}"

    def _get_project(self, client: httpx.Client, project_name: str) -> Dict[str, Any] | None:
        resp = client.get("/api/v2.0/projects", params={"name": project_name})
        resp.raise_for_status()
        items = resp.json() if resp.content else []
        if not items:
            return None
        return items[0]

    def ensure_tenant_project(self, tenant_id: str, project_spec: Dict[str, Any]) -> ProjectRef:
        project_name = self._project_name(tenant_id, project_spec)
        public = bool((project_spec or {}).get("public", False))
        storage_limit = int((project_spec or {}).get("storage_limit", -1))
        metadata = (project_spec or {}).get("metadata", {})
        with self._client() as client:
            existing = self._get_project(client, project_name)
            if existing:
                return ProjectRef(project_id=str(existing.get("project_id", project_name)), metadata={"name": project_name})
            payload = {
                "project_name": project_name,
                "public": public,
                "storage_limit": storage_limit,
                "metadata": metadata,
            }
            resp = client.post("/api/v2.0/projects", json=payload)
            if resp.status_code not in (200, 201, 409):
                raise RuntimeError(f"Failed to create Harbor project: {resp.status_code} {resp.text}")
            created = self._get_project(client, project_name)
            if not created:
                raise RuntimeError(f"Harbor project creation was not observable for '{project_name}'")
            return ProjectRef(project_id=str(created.get("project_id", project_name)), metadata={"name": project_name})

    def _resolve_user_id(self, client: httpx.Client, username: str) -> int | None:
        resp = client.get("/api/v2.0/users/search", params={"username": username})
        resp.raise_for_status()
        for user in resp.json() if resp.content else []:
            if user.get("username") == username:
                return int(user["user_id"])
        return None

    def _resolve_group_id(self, client: httpx.Client, group_name: str) -> int | None:
        resp = client.get("/api/v2.0/usergroups/search", params={"groupname": group_name})
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        for group in resp.json() if resp.content else []:
            if group.get("group_name") == group_name:
                return int(group["id"])
        return None

    def _resolve_role_id(self, role: str) -> int:
        role_id = ROLE_MAP.get(role.lower().replace("_", ""))
        if role_id is None:
            raise RuntimeError(f"Unsupported Harbor role '{role}'")
        return role_id

    def ensure_role_bindings(self, tenant_id: str, role_bindings: Dict[str, Any]) -> None:
        project_name = self._project_name(tenant_id, role_bindings)
        with self._client() as client:
            project = self._get_project(client, project_name)
            if not project:
                project = self.ensure_tenant_project(tenant_id, {"name": project_name}).metadata
                project = self._get_project(client, project_name)
            project_id = int(project["project_id"])
            members = role_bindings.get("members", [])
            if not isinstance(members, list):
                raise RuntimeError("role_bindings.members must be a list")
            for member in members:
                role = str(member.get("role", "developer"))
                role_id = self._resolve_role_id(role)
                entity_type = str(member.get("entity_type", "user")).lower()
                entity_name = member.get("name")
                if not entity_name:
                    raise RuntimeError("role_bindings.members[].name is required")
                payload: Dict[str, Any] = {"role_id": role_id}
                if entity_type == "user":
                    user_id = self._resolve_user_id(client, str(entity_name))
                    if user_id is None:
                        raise RuntimeError(f"Harbor user not found: {entity_name}")
                    payload["member_user"] = {"user_id": user_id}
                elif entity_type == "group":
                    group_id = self._resolve_group_id(client, str(entity_name))
                    if group_id is None:
                        raise RuntimeError(f"Harbor group not found: {entity_name}")
                    payload["member_group"] = {"id": group_id}
                else:
                    raise RuntimeError(f"Unsupported member entity_type '{entity_type}'")

                resp = client.post(f"/api/v2.0/projects/{project_id}/members", json=payload)
                if resp.status_code in (200, 201, 409):
                    continue
                raise RuntimeError(f"Failed to bind Harbor member '{entity_name}': {resp.status_code} {resp.text}")

    def create_robot_account(self, tenant_id: str, scope: Dict[str, Any]) -> RobotCredentials:
        project_name = str(scope.get("project_name") or f"{self._project_prefix}{tenant_id}")
        with self._client() as client:
            project = self._get_project(client, project_name)
            if not project:
                self.ensure_tenant_project(tenant_id, {"name": project_name})
                project = self._get_project(client, project_name)
            project_id = int(project["project_id"])

            robot_name = str(scope.get("name") or f"{tenant_id}-robot")
            duration = int(scope.get("duration", 30))
            permissions = scope.get("permissions")
            if not permissions:
                permissions = [
                    {
                        "kind": "project",
                        "namespace": project_name,
                        "access": [{"resource": "repository", "action": "pull"}],
                    }
                ]

            payload = {
                "name": robot_name,
                "description": f"Tenant robot for {tenant_id}",
                "duration": duration,
                "permissions": permissions,
                "disable": False,
            }
            resp = client.post(f"/api/v2.0/projects/{project_id}/robots", json=payload)
            if resp.status_code not in (200, 201, 409):
                raise RuntimeError(f"Failed to create Harbor robot account: {resp.status_code} {resp.text}")

            robot = resp.json() if resp.content else {}
            robot_id = robot.get("id")
            robot_full_name = robot.get("name") or f"robot${project_name}+{robot_name}"
            # Harbor returns secret only at creation time. Keep only reference token key, never secret value.
            secret_ref = f"harbor_robot/{tenant_id}/{robot_name}"
            if robot_id is not None:
                secret_ref = f"{secret_ref}/{robot_id}"
            return RobotCredentials(username=str(robot_full_name), secret_ref=secret_ref)
