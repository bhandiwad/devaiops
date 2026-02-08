from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from adapters.registry import AdapterRegistry
from artifacts.store import ArtifactRef, ArtifactStore
from config.loader import ConfigStore
from db.models import ArtifactRef as ArtifactRefModel
from db.models import ProvisioningRun
from db.repositories import ArtifactRefRepository, ProvisioningRunRepository
from plugins.terraform_runner import TerraformRunnerProvisionerAdapter


@dataclass
class ProvisioningResult:
    run: ProvisioningRun
    artifact: ArtifactRefModel | None


class ProvisioningService:
    def __init__(
        self,
        config_store: ConfigStore,
        registry: AdapterRegistry,
        artifact_store: ArtifactStore,
        repo_root: Path,
    ) -> None:
        self.config_store = config_store
        self.registry = registry
        self.artifact_store = artifact_store
        self.repo_root = repo_root
        self.terraform = TerraformRunnerProvisionerAdapter(platform_config=config_store.platform_config, artifact_store=artifact_store)

    def _workspace_dir(self, tenant_id: str) -> Path:
        base = self.config_store.platform_config.provisioning.get("terraform_work_dir")
        return Path(base) / tenant_id

    def _resolve_module_path(self, provisioner_ref: Dict[str, Any]) -> str:
        module_path = provisioner_ref.get("module_path")
        if not module_path:
            raise RuntimeError("provisioner_ref.module_path is required")
        path = Path(module_path)
        if not path.is_absolute():
            return str((self.repo_root / path).resolve())
        return str(path)

    def _tfvars_path(self, work_dir: Path, provisioner_ref: Dict[str, Any]) -> Path:
        vars_payload = provisioner_ref.get("vars", {})
        tfvars_path = work_dir / "vars.tfvars.json"
        tfvars_path.write_text(json.dumps(vars_payload))
        return tfvars_path

    def _store_artifact(self, tenant_id: str, name: str, payload: Dict[str, Any], repo: ArtifactRefRepository) -> ArtifactRefModel:
        artifact = self.artifact_store.put(name, json.dumps(payload).encode("utf-8"), "application/json", {"tenant_id": tenant_id})
        record = ArtifactRefModel(
            artifact_id=artifact.artifact_id,
            tenant_id=tenant_id,
            name=name,
            location=artifact.location,
            content_type="application/json",
            tags={"tenant_id": tenant_id},
        )
        return repo.create(record)

    async def plan(self, tenant_id: str, session) -> ProvisioningResult:
        tenant_spec = self.config_store.get_tenant_spec(tenant_id).model_dump()
        provisioner_ref = tenant_spec.get("provisioner_ref")
        if not provisioner_ref:
            raise RuntimeError("provisioner_ref is required")
        work_dir = self._workspace_dir(tenant_id)
        module_path = self._resolve_module_path(provisioner_ref)
        tfvars_path = self._tfvars_path(work_dir, provisioner_ref)
        env = self.terraform._terraform_env(provisioner_ref)

        self.terraform._init(module_path, work_dir, env)
        plan_file = "plan.tfplan"
        plan_proc = self.terraform._run(
            [self.terraform._config.binary, "plan", "-input=false", f"-var-file={tfvars_path}", f"-out={plan_file}"],
            work_dir,
            env,
        )
        if plan_proc.returncode != 0:
            raise RuntimeError(f"terraform plan failed: {plan_proc.stderr}")
        summary = self.terraform._capture_plan(work_dir, plan_file)

        artifact_repo = ArtifactRefRepository(session)
        artifact = await self._store_artifact(tenant_id, "terraform-plan.json", summary, artifact_repo)

        run = ProvisioningRun(
            run_id=str(uuid4()),
            tenant_id=tenant_id,
            operation="provision.plan",
            status="completed",
            plan_ref=artifact.artifact_id,
            apply_ref=None,
            error_detail={},
            correlation_id=None,
        )
        run_repo = ProvisioningRunRepository(session)
        await run_repo.create(run)
        return ProvisioningResult(run=run, artifact=artifact)

    async def apply(self, tenant_id: str, session) -> ProvisioningResult:
        tenant_spec = self.config_store.get_tenant_spec(tenant_id).model_dump()
        provisioner_ref = tenant_spec.get("provisioner_ref")
        if not provisioner_ref:
            raise RuntimeError("provisioner_ref is required")
        work_dir = self._workspace_dir(tenant_id)
        env = self.terraform._terraform_env(provisioner_ref)
        plan_file = work_dir / "plan.tfplan"
        if not plan_file.exists():
            raise RuntimeError("plan.tfplan not found; run plan first")

        apply_proc = self.terraform._apply(work_dir, env, str(plan_file))
        if apply_proc.returncode != 0:
            raise RuntimeError(f"terraform apply failed: {apply_proc.stderr}")

        output_proc = self.terraform._run([self.terraform._config.binary, "output", "-json"], work_dir, env)
        if output_proc.returncode != 0:
            raise RuntimeError(f"terraform output failed: {output_proc.stderr}")
        outputs = json.loads(output_proc.stdout)

        provider_profile = self.config_store.get_provider_profile(tenant_spec["provider_profile_id"]).model_dump()
        expected = (provider_profile.get("provisioning_defaults") or {}).get("expected_outputs", {})
        kubeconfig = outputs.get(expected.get("kubeconfig", ""), {}).get("value")
        server = outputs.get(expected.get("server", ""), {}).get("value")
        token = outputs.get(expected.get("token", ""), {}).get("value")
        ca = outputs.get(expected.get("ca", ""), {}).get("value")

        k8s_ref = tenant_spec.get("k8s_access_ref")
        if not k8s_ref or k8s_ref.get("type") != "vault_kv":
            raise RuntimeError("PROVISIONED tenants must define k8s_access_ref.type=vault_kv")
        secret_ref = k8s_ref.get("reference") or k8s_ref.get("value")
        if kubeconfig:
            payload = {"kubeconfig": kubeconfig}
        else:
            payload = {"server": server, "token": token, "ca": ca}
        self.registry.secrets().read_secret  # ensure adapter present
        if hasattr(self.registry.secrets(), "write_secret"):
            self.registry.secrets().write_secret(secret_ref, payload)

        artifact_repo = ArtifactRefRepository(session)
        artifact = await self._store_artifact(tenant_id, "terraform-apply.json", {"status": "applied"}, artifact_repo)

        run = ProvisioningRun(
            run_id=str(uuid4()),
            tenant_id=tenant_id,
            operation="provision.apply",
            status="completed",
            plan_ref=None,
            apply_ref=artifact.artifact_id,
            error_detail={},
            correlation_id=None,
        )
        run_repo = ProvisioningRunRepository(session)
        await run_repo.create(run)
        return ProvisioningResult(run=run, artifact=artifact)

    async def destroy(self, tenant_id: str, session) -> ProvisioningResult:
        tenant_spec = self.config_store.get_tenant_spec(tenant_id).model_dump()
        provisioner_ref = tenant_spec.get("provisioner_ref")
        if not provisioner_ref:
            raise RuntimeError("provisioner_ref is required")
        work_dir = self._workspace_dir(tenant_id)
        env = self.terraform._terraform_env(provisioner_ref)
        destroy_proc = self.terraform._destroy(work_dir, env)
        if destroy_proc.returncode != 0:
            raise RuntimeError(f"terraform destroy failed: {destroy_proc.stderr}")

        artifact_repo = ArtifactRefRepository(session)
        artifact = await self._store_artifact(tenant_id, "terraform-destroy.json", {"status": "destroyed"}, artifact_repo)

        run = ProvisioningRun(
            run_id=str(uuid4()),
            tenant_id=tenant_id,
            operation="provision.destroy",
            status="completed",
            plan_ref=None,
            apply_ref=artifact.artifact_id,
            error_detail={},
            correlation_id=None,
        )
        run_repo = ProvisioningRunRepository(session)
        await run_repo.create(run)
        return ProvisioningResult(run=run, artifact=artifact)
