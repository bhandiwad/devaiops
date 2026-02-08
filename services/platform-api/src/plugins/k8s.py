from __future__ import annotations

import tempfile
from typing import Any, Dict, List

from kubernetes import client, config
from kubernetes.client import ApiException
import yaml

from adapters.interfaces import (
    BootstrapResult,
    CapabilityProbeAdapter,
    CapabilityReport,
    ClusterAccess,
    ClusterRef,
    Events,
    K8sAdapter,
    RegistrarAdapter,
    Resource,
    Snapshot,
)


class DefaultCapabilityProbe(CapabilityProbeAdapter):
    """Capability probe that merges provider defaults with lightweight cluster checks."""

    def _api_client_from_access(self, cluster_access: ClusterAccess) -> client.ApiClient | None:
        if cluster_access.kubeconfig:
            try:
                config.load_kube_config_from_dict(yaml.safe_load(cluster_access.kubeconfig))
                return client.ApiClient()
            except Exception:
                return None
        server = (cluster_access.metadata or {}).get("server")
        token = (cluster_access.metadata or {}).get("token")
        ca = (cluster_access.metadata or {}).get("ca")
        if not server or not token:
            return None
        cfg = client.Configuration()
        cfg.host = server
        cfg.api_key = {"authorization": f"Bearer {token}"}
        if ca:
            with tempfile.NamedTemporaryFile(delete=False) as handle:
                handle.write(ca.encode("utf-8"))
                cfg.ssl_ca_cert = handle.name
        return client.ApiClient(cfg)

    def probe(self, cluster_access: ClusterAccess, provider_profile: Dict[str, Any]) -> CapabilityReport:
        capabilities = dict((provider_profile or {}).get("capabilities", {}) or {})
        warnings: List[str] = []
        api_client = self._api_client_from_access(cluster_access)
        if not api_client:
            warnings.append("cluster probe used provider profile defaults only")
            return CapabilityReport(capabilities=capabilities, warnings=warnings)
        version_api = client.VersionApi(api_client)
        try:
            version = version_api.get_code()
            capabilities["k8s_version"] = f"{version.major}.{version.minor}"
        except Exception as exc:
            warnings.append(f"failed to read Kubernetes version: {exc}")
        try:
            core = client.CoreV1Api(api_client)
            ns = core.list_namespace(limit=1)
            capabilities["k8s_reachable"] = True
            capabilities["has_namespaces"] = len(ns.items) > 0
        except Exception as exc:
            capabilities["k8s_reachable"] = False
            warnings.append(f"failed to query namespaces: {exc}")
        return CapabilityReport(capabilities=capabilities, warnings=warnings)


class DefaultRegistrarAdapter(RegistrarAdapter):
    """Registrar that ensures tenant namespace(s) exist as bootstrap baseline."""

    def bootstrap(
        self,
        cluster_access: ClusterAccess,
        tenant_spec,
        provider_profile,
        capability_report: CapabilityReport,
    ) -> BootstrapResult:
        namespace = (tenant_spec or {}).get("default_namespace") or (tenant_spec or {}).get("tenant_id")
        if not namespace:
            return BootstrapResult(status="ok", detail={"message": "no namespace requested"})
        api_client: client.ApiClient | None = DefaultCapabilityProbe()._api_client_from_access(cluster_access)
        if not api_client:
            return BootstrapResult(status="ok", detail={"message": "no direct cluster bootstrap in this mode"})
        core = client.CoreV1Api(api_client)
        body = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
        try:
            core.create_namespace(body=body)
            return BootstrapResult(status="ok", detail={"namespace": namespace, "created": True})
        except ApiException as exc:
            if exc.status == 409:
                return BootstrapResult(status="ok", detail={"namespace": namespace, "created": False})
            raise RuntimeError(f"failed to bootstrap namespace '{namespace}': {exc}") from exc


class DefaultK8sAdapter(K8sAdapter):
    """Lightweight Kubernetes adapter for baseline operations."""

    def _api_client(self, cluster_ref: ClusterRef) -> client.ApiClient:
        metadata = cluster_ref.metadata or {}
        if metadata.get("kubeconfig_path"):
            config.load_kube_config(config_file=metadata["kubeconfig_path"])
            return client.ApiClient()
        if metadata.get("kubeconfig_dict"):
            config.load_kube_config_from_dict(metadata["kubeconfig_dict"])
            return client.ApiClient()
        server = metadata.get("server")
        token = metadata.get("token")
        ca = metadata.get("ca")
        if not server or not token:
            raise RuntimeError("cluster_ref must include kubeconfig_path/kubeconfig_dict or server/token")
        cfg = client.Configuration()
        cfg.host = server
        cfg.api_key = {"authorization": f"Bearer {token}"}
        if ca:
            with tempfile.NamedTemporaryFile(delete=False) as handle:
                handle.write(ca.encode("utf-8"))
                cfg.ssl_ca_cert = handle.name
        return client.ApiClient(cfg)

    def _label_selector(self, selectors: Dict[str, Any]) -> str | None:
        if "label_selector" in selectors:
            return selectors["label_selector"]
        labels = selectors.get("labels")
        if isinstance(labels, dict):
            return ",".join([f"{k}={v}" for k, v in labels.items()])
        return None

    def get_workload_snapshot(self, cluster_ref: ClusterRef, selectors) -> Snapshot:
        api_client = self._api_client(cluster_ref)
        core = client.CoreV1Api(api_client)
        apps = client.AppsV1Api(api_client)
        namespace = selectors.get("namespace") or "default"
        label_selector = self._label_selector(selectors or {})
        deployments = apps.list_namespaced_deployment(namespace=namespace, label_selector=label_selector)
        pods = core.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
        resources: List[Dict[str, Any]] = [d.to_dict() for d in deployments.items]
        resources.extend([p.to_dict() for p in pods.items])
        return Snapshot(resources=resources)

    def get_events(self, cluster_ref: ClusterRef, namespace: str, since: str | None = None) -> Events:
        api_client = self._api_client(cluster_ref)
        core = client.CoreV1Api(api_client)
        events = core.list_namespaced_event(namespace=namespace)
        entries = [e.to_dict() for e in events.items]
        return Events(entries=entries)

    def get_resource(self, cluster_ref: ClusterRef, gvk, name: str, namespace: str) -> Resource:
        api_client = self._api_client(cluster_ref)
        kind = str((gvk or {}).get("kind", "")).lower()
        if kind == "deployment":
            obj = client.AppsV1Api(api_client).read_namespaced_deployment(name=name, namespace=namespace)
            return Resource(body=obj.to_dict())
        if kind == "pod":
            obj = client.CoreV1Api(api_client).read_namespaced_pod(name=name, namespace=namespace)
            return Resource(body=obj.to_dict())
        raise RuntimeError(f"Unsupported kind for DefaultK8sAdapter.get_resource: {gvk}")
