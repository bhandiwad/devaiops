from types import SimpleNamespace

import httpx

from plugins.harbor import HarborRegistryAdapter


def _cfg():
    return SimpleNamespace(
        registry={"harbor": {"base_url": "http://harbor.local", "project_prefix": "tenant-"}},
        integrations={"timeout_seconds": 5},
    )


def test_harbor_project_role_robot(monkeypatch):
    monkeypatch.setenv("HARBOR_ADMIN_PASSWORD", "secret")

    state = {
        "project_created": False,
        "members_created": 0,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/v2.0/projects" and request.method == "GET":
            name = request.url.params.get("name")
            if name == "tenant-acme" and state["project_created"]:
                return httpx.Response(200, json=[{"project_id": 42, "name": name}])
            return httpx.Response(200, json=[])
        if path == "/api/v2.0/projects" and request.method == "POST":
            state["project_created"] = True
            return httpx.Response(201, json={})
        if path == "/api/v2.0/users/search":
            return httpx.Response(200, json=[{"user_id": 7, "username": "alice"}])
        if path == "/api/v2.0/projects/42/members" and request.method == "POST":
            state["members_created"] += 1
            return httpx.Response(201, json={})
        if path == "/api/v2.0/projects/42/robots" and request.method == "POST":
            return httpx.Response(201, json={"id": 123, "name": "robot$tenant-acme+ci"})
        return httpx.Response(404, json={"error": path})

    transport = httpx.MockTransport(handler)

    adapter = HarborRegistryAdapter(platform_config=_cfg())

    def _client_factory():
        return httpx.Client(base_url="http://harbor.local", transport=transport)

    monkeypatch.setattr(adapter, "_client", _client_factory)

    project = adapter.ensure_tenant_project("acme", {})
    assert project.project_id == "42"

    adapter.ensure_role_bindings(
        "acme",
        {
            "members": [
                {"entity_type": "user", "name": "alice", "role": "developer"},
            ]
        },
    )
    assert state["members_created"] == 1

    creds = adapter.create_robot_account("acme", {"name": "ci"})
    assert creds.username.startswith("robot$")
    assert creds.secret_ref.startswith("harbor_robot/acme/ci/")
