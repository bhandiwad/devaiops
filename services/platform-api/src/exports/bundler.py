from __future__ import annotations

import io
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from aiops.redaction import redact_payload
from artifacts.service import ArtifactService
from db.models import ExportBundle
from db.repositories import (
    AuditRepository,
    DriftRunRepository,
    ExportBundleRepository,
    IncidentRepository,
    PolicyDecisionRepository,
    ProvisioningRunRepository,
    RunbookExecutionRepository,
    TenantRepository,
)


@dataclass
class ExportResult:
    export_id: str
    artifact_ref: str
    status: str


class TenantExportBundler:
    def __init__(
        self,
        tenant_repo: TenantRepository,
        audit_repo: AuditRepository,
        policy_repo: PolicyDecisionRepository,
        incident_repo: IncidentRepository,
        provisioning_repo: ProvisioningRunRepository,
        runbook_repo: RunbookExecutionRepository,
        drift_repo: DriftRunRepository,
        export_repo: ExportBundleRepository,
        artifact_service: ArtifactService,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._audit_repo = audit_repo
        self._policy_repo = policy_repo
        self._incident_repo = incident_repo
        self._provisioning_repo = provisioning_repo
        self._runbook_repo = runbook_repo
        self._drift_repo = drift_repo
        self._export_repo = export_repo
        self._artifact_service = artifact_service

    async def export(self, tenant_id: str, filters: Optional[Dict[str, Any]] = None) -> ExportResult:
        export_id = str(uuid4())
        await self._export_repo.create(
            ExportBundle(
                export_id=export_id,
                tenant_id=tenant_id,
                status="RUNNING",
                filters=filters or {},
            )
        )
        return await self.export_existing(export_id, tenant_id)

    async def export_existing(self, export_id: str, tenant_id: str) -> ExportResult:
        bundle = await self._export_repo.get(export_id)
        if not bundle:
            raise RuntimeError("Export bundle not found")

        tenant = await self._tenant_repo.get(tenant_id)
        audits = await self._audit_repo.list_for_tenant(tenant_id)
        policies = await self._policy_repo.list_for_tenant(tenant_id)
        incidents = await self._incident_repo.list_for_tenant(tenant_id)
        provision_runs = await self._provisioning_repo.list_for_tenant(tenant_id)
        runbooks = await self._runbook_repo.list_for_tenant(tenant_id)
        drifts = await self._drift_repo.list_for_tenant(tenant_id)

        def _clean(model):
            data = dict(model.__dict__)
            data.pop("_sa_instance_state", None)
            return data

        payload = {
            "tenant": _clean(tenant) if tenant else {},
            "audit_events": [_clean(a) for a in audits],
            "policy_decisions": [_clean(p) for p in policies],
            "incidents": [_clean(i) for i in incidents],
            "provisioning_runs": [_clean(r) for r in provision_runs],
            "runbook_executions": [_clean(r) for r in runbooks],
            "drift_runs": [_clean(d) for d in drifts],
        }
        redacted, _ = redact_payload(payload)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr("metadata.json", json.dumps({"tenant_id": tenant_id, "generated_at": datetime.utcnow().isoformat()}))
            zipf.writestr("export.json", json.dumps(redacted, indent=2, default=str))
        buffer.seek(0)

        artifact = await self._artifact_service.put(
            tenant_id=tenant_id,
            name=f"tenant-export-{tenant_id}.zip",
            data=buffer.read(),
            content_type="application/zip",
            tags={"type": "export"},
        )

        bundle.status = "COMPLETED"
        bundle.artifact_ref = artifact.artifact_id
        await self._export_repo.update(bundle)
        return ExportResult(export_id=export_id, artifact_ref=artifact.artifact_id, status="COMPLETED")
