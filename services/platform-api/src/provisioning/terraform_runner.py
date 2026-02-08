from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

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
        raise NotImplementedError("Use plan/apply endpoints for provisioning")

    def upgrade(self, tenant_id: str, plan: Dict[str, Any]) -> ClusterAccess:
        raise NotImplementedError

    def deprovision(self, tenant_id: str) -> None:
        raise NotImplementedError
