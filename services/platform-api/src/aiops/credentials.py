from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

import yaml

from adapters.interfaces import ClusterAccess, ClusterRef
from adapters.registry import AdapterRegistry
from auth.rbac import is_dev_auth_enabled


def _load_kubeconfig_file(path: Path) -> str:
    if not path.exists():
        raise RuntimeError(f"kubeconfig file not found: {path}")
    return path.read_text()


def resolve_k8s_access(
    tenant_spec: Dict[str, Any],
    registry: AdapterRegistry,
    repo_root: Path,
) -> Tuple[ClusterAccess, ClusterRef]:
    k8s_ref = tenant_spec.get("k8s_access_ref")
    if not k8s_ref:
        raise RuntimeError("k8s_access_ref is required")

    ref_type = k8s_ref.get("type")
    reference = k8s_ref.get("reference") or k8s_ref.get("value")
    if not reference:
        raise RuntimeError("k8s_access_ref.reference is required")

    if ref_type == "kubeconfig_file":
        if not is_dev_auth_enabled():
            raise RuntimeError("kubeconfig_file is only allowed in DEV_AUTH mode")
        path = Path(reference)
        if not path.is_absolute():
            path = (repo_root / path).resolve()
        kubeconfig = _load_kubeconfig_file(path)
        access = ClusterAccess(kubeconfig=kubeconfig, metadata={"access_ref": k8s_ref})
        ref = ClusterRef(cluster_id=tenant_spec["tenant_id"], metadata={"kubeconfig_path": str(path)})
        return access, ref

    if ref_type == "vault_kv":
        secret = registry.secrets().read_secret(reference)
        kubeconfig = secret.get("kubeconfig")
        if kubeconfig:
            access = ClusterAccess(kubeconfig=kubeconfig, metadata={"access_ref": k8s_ref})
            ref = ClusterRef(
                cluster_id=tenant_spec["tenant_id"],
                metadata={"kubeconfig_dict": yaml.safe_load(kubeconfig)},
            )
            return access, ref
        server = secret.get("server")
        token = secret.get("token")
        ca = secret.get("ca")
        if not server or not token:
            raise RuntimeError("Vault secret must include server and token")
        access = ClusterAccess(kubeconfig=None, metadata={"access_ref": k8s_ref})
        ref = ClusterRef(
            cluster_id=tenant_spec["tenant_id"],
            metadata={"server": server, "token": token, "ca": ca},
        )
        return access, ref

    if ref_type in {"external_secret_ref", "bootstrap_token"}:
        raise RuntimeError(f"k8s_access_ref type '{ref_type}' not implemented")

    raise RuntimeError("k8s_access_ref type is required")
