from __future__ import annotations

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
    """Stub capability probe adapter."""

    def probe(self, cluster_access: ClusterAccess, provider_profile) -> CapabilityReport:
        raise NotImplementedError("DefaultCapabilityProbe.probe is not implemented")


class DefaultRegistrarAdapter(RegistrarAdapter):
    """Stub registrar adapter."""

    def bootstrap(
        self,
        cluster_access: ClusterAccess,
        tenant_spec,
        provider_profile,
        capability_report: CapabilityReport,
    ) -> BootstrapResult:
        raise NotImplementedError("DefaultRegistrarAdapter.bootstrap is not implemented")


class DefaultK8sAdapter(K8sAdapter):
    """Stub Kubernetes adapter."""

    def get_workload_snapshot(self, cluster_ref: ClusterRef, selectors) -> Snapshot:
        raise NotImplementedError("DefaultK8sAdapter.get_workload_snapshot is not implemented")

    def get_events(self, cluster_ref: ClusterRef, namespace: str, since: str | None = None) -> Events:
        raise NotImplementedError("DefaultK8sAdapter.get_events is not implemented")

    def get_resource(self, cluster_ref: ClusterRef, gvk, name: str, namespace: str) -> Resource:
        raise NotImplementedError("DefaultK8sAdapter.get_resource is not implemented")
