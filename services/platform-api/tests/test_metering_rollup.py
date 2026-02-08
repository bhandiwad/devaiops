from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
from types import SimpleNamespace

import pytest

from db.models import Base, MeteringSample
from db.repositories import (
    AuditRepository,
    DriftRunRepository,
    ExportBundleRepository,
    MeteringRollupRepository,
    MeteringSampleRepository,
    RunbookExecutionRepository,
)
from db.session import create_database
from metering.collector import MeteringCollector


@pytest.mark.asyncio
async def test_metering_rollup_sums_metrics(tmp_path):
    db = create_database(f"sqlite+aiosqlite:///{tmp_path}/metering.db")
    async with db.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with db.session_factory() as session:
        sample_repo = MeteringSampleRepository(session)
        rollup_repo = MeteringRollupRepository(session)
        await sample_repo.create(
            MeteringSample(
                sample_id=str(uuid4()),
                tenant_id="t1",
                captured_at=datetime.now(timezone.utc),
                metrics={"api_calls": 10, "pod_hours_estimate": 4},
            )
        )
        await sample_repo.create(
            MeteringSample(
                sample_id=str(uuid4()),
                tenant_id="t1",
                captured_at=datetime.now(timezone.utc),
                metrics={"api_calls": 5, "pod_hours_estimate": 2},
            )
        )
        collector = MeteringCollector(
            config_store=SimpleNamespace(),
            registry=SimpleNamespace(),
            sample_repo=sample_repo,
            rollup_repo=rollup_repo,
            audit_repo=AuditRepository(session),
            drift_repo=DriftRunRepository(session),
            runbook_repo=RunbookExecutionRepository(session),
            export_repo=ExportBundleRepository(session),
        )
        rollup = await collector.rollup("t1", granularity="daily")
        await session.commit()
        assert rollup is not None
        assert rollup.metrics["api_calls"] == 15
        assert rollup.metrics["pod_hours_estimate"] == 6
