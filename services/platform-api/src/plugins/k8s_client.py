from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

import tempfile

from kubernetes import client, config

from adapters.interfaces import ClusterRef, Events, K8sAdapter, Resource, Snapshot


class K8sClientAdapter(K8sAdapter):
    """Read-only Kubernetes adapter using the official client."""

    def _load_client(self, cluster_ref: ClusterRef) -> client.ApiClient:
        if cluster_ref.metadata.get("kubeconfig_path"):
            config.load_kube_config(config_file=cluster_ref.metadata.get("kubeconfig_path"))
            return client.ApiClient()
        if cluster_ref.metadata.get("kubeconfig_dict"):
            config.load_kube_config_from_dict(cluster_ref.metadata.get("kubeconfig_dict"))
            return client.ApiClient()
        server = cluster_ref.metadata.get("server")
        token = cluster_ref.metadata.get("token")
        ca = cluster_ref.metadata.get("ca")
        if server and token:
            cfg = client.Configuration()
            cfg.host = server
            cfg.api_key = {"authorization": f"Bearer {token}"}
            if ca:
                with tempfile.NamedTemporaryFile(delete=False) as handle:
                    handle.write(ca.encode("utf-8"))
                    cfg.ssl_ca_cert = handle.name
            return client.ApiClient(cfg)
        raise RuntimeError("cluster_ref metadata must include kubeconfig_path or server/token")

    def _label_selector(self, selectors: Dict[str, Any]) -> str | None:
        if not selectors:
            return None
        if "label_selector" in selectors:
            return selectors["label_selector"]
        labels = selectors.get("labels")
        if isinstance(labels, dict):
            return ",".join([f"{k}={v}" for k, v in labels.items()])
        return None

    def get_workload_snapshot(self, cluster_ref: ClusterRef, selectors: Dict[str, Any]) -> Snapshot:
        api_client = self._load_client(cluster_ref)
        core = client.CoreV1Api(api_client)
        apps = client.AppsV1Api(api_client)
        namespace = selectors.get("namespace") or "default"
        label_selector = self._label_selector(selectors)

        deployments = apps.list_namespaced_deployment(namespace=namespace, label_selector=label_selector)
        pods = core.list_namespaced_pod(namespace=namespace, label_selector=label_selector)

        resources: List[Dict[str, Any]] = []
        resources.extend([d.to_dict() for d in deployments.items])
        resources.extend([p.to_dict() for p in pods.items])
        return Snapshot(resources=resources)

    def get_events(self, cluster_ref: ClusterRef, namespace: str, since: str | None = None) -> Events:
        api_client = self._load_client(cluster_ref)
        core = client.CoreV1Api(api_client)
        events = core.list_namespaced_event(namespace=namespace)
        entries = [event.to_dict() for event in events.items]
        if since:
            try:
                since_dt = datetime.fromisoformat(since)
                entries = [
                    e
                    for e in entries
                    if e.get("last_timestamp") and datetime.fromisoformat(e["last_timestamp"]) >= since_dt
                ]
            except ValueError:
                pass
        return Events(entries=entries)

    def get_resource(self, cluster_ref: ClusterRef, gvk: Dict[str, str], name: str, namespace: str) -> Resource:
        raise NotImplementedError("Generic resource fetch is not implemented")
