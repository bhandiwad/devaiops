import json
import os

import httpx
import pytest

from adapters.interfaces import ClusterAccess
from plugins.argocd import ArgoCDGitOpsAdapter


@pytest.fixture()
def kubeconfig():
    return """
apiVersion: v1
kind: Config
clusters:
- name: test
  cluster:
    server: https://k8s.example
    certificate-authority-data: dGVzdA==
users:
- name: user
  user:
    token: testtoken
contexts:
- name: ctx
  context:
    cluster: test
    user: user
current-context: ctx
"""


def test_argocd_register_cluster(monkeypatch, kubeconfig):
    monkeypatch.setenv("ARGOCD_SERVER", "https://argocd.example")
    monkeypatch.setenv("ARGOCD_TOKEN", "token")

    requests = []

    def handler(request: httpx.Request):
        requests.append(request)
        return httpx.Response(200, json={"status": "ok"})

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://argocd.example")
    adapter = ArgoCDGitOpsAdapter(platform_config=None, client=client)
    adapter.register_cluster("tenant-a", ClusterAccess(kubeconfig=kubeconfig), {})

    assert requests
    req = requests[0]
    body = json.loads(req.content)
    assert body["name"] == "tenant-a-cluster"
    assert body["server"] == "https://k8s.example"
