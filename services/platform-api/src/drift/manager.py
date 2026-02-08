from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
from uuid import uuid4

import json

from artifacts.service import ArtifactService
from db.models import DriftRun
from db.repositories import DriftRunRepository
from drift.detectors import DriftDetector, DriftResult


@dataclass
class DriftRunResult:
    run_id: str
    detector_type: str
    status: str
    summary: Dict[str, object]


class DriftManager:
    def __init__(
        self,
        detectors: Dict[str, DriftDetector],
        repo: DriftRunRepository,
        artifact_service: ArtifactService,
    ) -> None:
        self._detectors = detectors
        self._repo = repo
        self._artifact_service = artifact_service

    async def run(self, tenant_id: str, detector_names: Optional[List[str]] = None) -> List[DriftRunResult]:
        results: List[DriftRunResult] = []
        names = detector_names or list(self._detectors.keys())
        for name in names:
            detector = self._detectors.get(name)
            if not detector:
                continue
            run_id = str(uuid4())
            drift_run = DriftRun(
                run_id=run_id,
                tenant_id=tenant_id,
                detector_type=name,
                status="RUNNING",
                summary={},
            )
            await self._repo.create(drift_run)
            result: DriftResult
            try:
                result = detector.detect(tenant_id)
                artifact = await self._artifact_service.put(
                    tenant_id=tenant_id,
                    name=f"drift-{name}.json",
                    data=json.dumps(result.summary, indent=2).encode("utf-8"),
                    content_type="application/json",
                    tags={"detector": name},
                )
                drift_run.status = result.status
                drift_run.summary = result.summary
                drift_run.artifact_ref = artifact.artifact_id
                results.append(
                    DriftRunResult(
                        run_id=run_id,
                        detector_type=name,
                        status=result.status,
                        summary=result.summary,
                    )
                )
            except Exception as exc:
                drift_run.status = "ERROR"
                drift_run.summary = {"error": str(exc)}
                results.append(
                    DriftRunResult(run_id=run_id, detector_type=name, status="ERROR", summary={"error": str(exc)})
                )
            await self._repo.update(drift_run)
        return results
