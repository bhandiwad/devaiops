from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import httpx

from adapters.interfaces import ClusterAccess, ProvisionerAdapter
from artifacts.store import ArtifactRef, ArtifactStore


@dataclass
class TerraformRunnerConfig:
    binary: str
    base_work_dir: Path


class TerraformRunnerProvisionerAdapter(ProvisionerAdapter):
    """Terraform runner provisioner (plan/apply/destroy)."""

    def __init__(self, platform_config=None, artifact_store: ArtifactStore | None = None) -> None:
        if not platform_config:
            raise RuntimeError("PlatformConfig is required")
        provisioning = (platform_config.provisioning or {}) if hasattr(platform_config, "provisioning") else {}
        base_dir = provisioning.get("terraform_work_dir", "/tmp/aiops-terraform")
        self._config = TerraformRunnerConfig(binary=provisioning.get("terraform_binary", "terraform"), base_work_dir=Path(base_dir))
        self._config.base_work_dir.mkdir(parents=True, exist_ok=True)
        self._artifact_store = artifact_store

    def _run(self, args: list[str], work_dir: Path, env: Dict[str, str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            args,
            cwd=str(work_dir),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def _terraform_env(self, provisioner_ref: Dict[str, Any]) -> Dict[str, str]:
        env = os.environ.copy()
        backend = provisioner_ref.get("backend") or {}
        for key, value in backend.items():
            env[f"TF_BACKEND_{key.upper()}"] = str(value)
        return env

    def _init(self, module_path: str, work_dir: Path, env: Dict[str, str]) -> None:
        work_dir.mkdir(parents=True, exist_ok=True)
        args = [self._config.binary, "init", "-input=false"]
        if module_path:
            args.append(module_path)
        result = self._run(args, work_dir, env)
        if result.returncode != 0:
            raise RuntimeError(f"terraform init failed: {result.stderr}")

    def _plan(
        self,
        work_dir: Path,
        env: Dict[str, str],
        plan_file: str,
        extra_args: list[str] | None = None,
    ) -> subprocess.CompletedProcess:
        args = [self._config.binary, "plan", "-input=false", f"-out={plan_file}"]
        if extra_args:
            args.extend(extra_args)
        return self._run(args, work_dir, env)

    def _apply(self, work_dir: Path, env: Dict[str, str], plan_file: str) -> subprocess.CompletedProcess:
        args = [self._config.binary, "apply", "-input=false", plan_file]
        return self._run(args, work_dir, env)

    def _destroy(self, work_dir: Path, env: Dict[str, str]) -> subprocess.CompletedProcess:
        args = [self._config.binary, "destroy", "-input=false", "-auto-approve"]
        return self._run(args, work_dir, env)

    def _sanitize_plan(self, plan_json: Dict[str, Any]) -> Dict[str, Any]:
        summary = {"add": 0, "change": 0, "destroy": 0, "resources": []}
        for change in plan_json.get("resource_changes", []) or []:
            actions = change.get("change", {}).get("actions", [])
            address = change.get("address")
            summary["resources"].append({"address": address, "actions": actions})
            if "create" in actions:
                summary["add"] += 1
            if "update" in actions:
                summary["change"] += 1
            if "delete" in actions:
                summary["destroy"] += 1
        return summary

    def _capture_plan(self, work_dir: Path, plan_file: str) -> Dict[str, Any]:
        show = self._run([self._config.binary, "show", "-json", plan_file], work_dir, os.environ.copy())
        if show.returncode != 0:
            raise RuntimeError(f"terraform show failed: {show.stderr}")
        plan_json = json.loads(show.stdout)
        return self._sanitize_plan(plan_json)

    def _work_dir(self, tenant_id: str) -> Path:
        return self._config.base_work_dir / tenant_id

    def _apply_workspace(self, work_dir: Path, env: Dict[str, str], workspace: str | None) -> None:
        if not workspace:
            return
        select = self._run([self._config.binary, "workspace", "select", workspace], work_dir, env)
        if select.returncode != 0:
            new = self._run([self._config.binary, "workspace", "new", workspace], work_dir, env)
            if new.returncode != 0:
                raise RuntimeError(f"terraform workspace init failed: {new.stderr}")

    def _var_args(self, provisioner_ref: Dict[str, Any]) -> list[str]:
        args: list[str] = []
        vars_block = provisioner_ref.get("vars", {}) or {}
        opaque = vars_block.get("opaque", {}) or {}
        for key, value in opaque.items():
            args.append(f"-var={key}={value}")
        return args

    def _write_vault_secret(self, secret_ref: str, payload: Dict[str, Any]) -> None:
        vault_addr = os.getenv("VAULT_ADDR")
        vault_token = os.getenv("VAULT_TOKEN")
        if not vault_addr or not vault_token:
            raise RuntimeError("VAULT_ADDR and VAULT_TOKEN are required for vault_kv secret writes")
        if not secret_ref.startswith("kv/"):
            raise RuntimeError("Only kv/ paths are supported for Vault secret writes")
        url = f"{vault_addr.rstrip('/')}/v1/{secret_ref}"
        resp = httpx.post(url, headers={"X-Vault-Token": vault_token}, json={"data": payload}, timeout=10.0)
        if resp.status_code >= 400:
            raise RuntimeError(f"Vault write failed {resp.status_code}: {resp.text}")

    def _cluster_access_from_outputs(
        self,
        outputs: Dict[str, Any],
        provider_profile: Dict[str, Any],
        tenant_spec: Dict[str, Any],
    ) -> ClusterAccess:
        expected = (provider_profile.get("provisioning_defaults") or {}).get("expected_outputs", {})
        kubeconfig_key = expected.get("kubeconfig", "kubeconfig")
        server_key = expected.get("server", "cluster_endpoint")
        token_key = expected.get("token", "cluster_token")
        ca_key = expected.get("ca", "cluster_ca")

        kubeconfig = (outputs.get(kubeconfig_key) or {}).get("value")
        server = (outputs.get(server_key) or {}).get("value")
        token = (outputs.get(token_key) or {}).get("value")
        ca = (outputs.get(ca_key) or {}).get("value")
        metadata: Dict[str, Any] = {"output_keys": sorted(outputs.keys())}

        access_ref = tenant_spec.get("k8s_access_ref") or {}
        ref_type = access_ref.get("type")
        reference = access_ref.get("reference") or access_ref.get("value")
        if ref_type == "vault_kv" and reference:
            payload = {"kubeconfig": kubeconfig} if kubeconfig else {"server": server, "token": token, "ca": ca}
            self._write_vault_secret(reference, payload)
            metadata["k8s_access_ref"] = reference
        if kubeconfig:
            return ClusterAccess(kubeconfig=kubeconfig, metadata=metadata)
        if server and token:
            metadata.update({"server": server, "token": token, "ca": ca})
            return ClusterAccess(kubeconfig=None, metadata=metadata)
        raise RuntimeError(
            "Terraform outputs did not include cluster access data. "
            "Check provider_profile.provisioning_defaults.expected_outputs mapping."
        )

    def plan_drift(self, tenant_spec: Dict[str, Any]) -> Dict[str, Any]:
        provisioner_ref = tenant_spec.get("provisioner_ref") or {}
        tenant_id = tenant_spec.get("tenant_id")
        if not tenant_id:
            raise RuntimeError("tenant_id is required in tenant_spec")
        module_path = provisioner_ref.get("module_path")
        if not module_path:
            raise RuntimeError("provisioner_ref.module_path is required")
        work_dir = self._work_dir(tenant_id)
        env = self._terraform_env(provisioner_ref)
        self._init(module_path, work_dir, env)
        self._apply_workspace(work_dir, env, provisioner_ref.get("workspace"))
        plan_file = "drift.tfplan"
        args = self._var_args(provisioner_ref)
        result = self._plan(work_dir, env, plan_file, extra_args=["-detailed-exitcode"] + args)
        if result.returncode not in (0, 2):
            raise RuntimeError(f"terraform plan failed: {result.stderr}")
        summary = self._capture_plan(work_dir, plan_file)
        summary["exit_code"] = result.returncode
        return summary

    def provision(self, tenant_spec: Dict[str, Any], provider_profile: Dict[str, Any]) -> ClusterAccess:
        tenant_id = tenant_spec.get("tenant_id")
        if not tenant_id:
            raise RuntimeError("tenant_spec.tenant_id is required")
        provisioner_ref = tenant_spec.get("provisioner_ref") or {}
        module_path = provisioner_ref.get("module_path")
        if not module_path:
            raise RuntimeError("tenant_spec.provisioner_ref.module_path is required")

        work_dir = self._work_dir(tenant_id)
        env = self._terraform_env(provisioner_ref)
        self._init(module_path, work_dir, env)
        self._apply_workspace(work_dir, env, provisioner_ref.get("workspace"))

        plan_file = "provision.tfplan"
        plan = self._plan(work_dir, env, plan_file, extra_args=self._var_args(provisioner_ref))
        if plan.returncode != 0:
            raise RuntimeError(f"terraform plan failed: {plan.stderr}")

        apply = self._apply(work_dir, env, plan_file)
        if apply.returncode != 0:
            raise RuntimeError(f"terraform apply failed: {apply.stderr}")

        output = self._run([self._config.binary, "output", "-json"], work_dir, env)
        if output.returncode != 0:
            raise RuntimeError(f"terraform output failed: {output.stderr}")
        outputs = json.loads(output.stdout)
        return self._cluster_access_from_outputs(outputs, provider_profile, tenant_spec)

    def upgrade(self, tenant_id: str, plan: Dict[str, Any]) -> ClusterAccess:
        tenant_spec = {
            "tenant_id": tenant_id,
            "provisioner_ref": plan.get("provisioner_ref") or {},
            "k8s_access_ref": plan.get("k8s_access_ref") or {},
        }
        provider_profile = plan.get("provider_profile") or {}
        return self.provision(tenant_spec, provider_profile)

    def deprovision(self, tenant_id: str) -> None:
        work_dir = self._work_dir(tenant_id)
        if not work_dir.exists():
            raise RuntimeError(f"No terraform workspace found for tenant '{tenant_id}'")
        env = os.environ.copy()
        destroy = self._destroy(work_dir, env)
        if destroy.returncode != 0:
            raise RuntimeError(f"terraform destroy failed: {destroy.stderr}")
