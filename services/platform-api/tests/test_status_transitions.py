import asyncio

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from db.models import Base, Tenant
from db.repositories import TenantRepository, TenantStatusHistoryRepository
from db.services import TenantStatusService


@pytest.mark.asyncio
async def test_status_transitions_stored():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        tenant_repo = TenantRepository(session)
        history_repo = TenantStatusHistoryRepository(session)
        status_service = TenantStatusService(tenant_repo, history_repo)

        tenant = Tenant(
            tenant_id="tenant-a",
            display_name="Tenant A",
            mode="BYOC",
            provider_profile_id="generic",
            status="PROVISIONING",
            metadata_={},
        )
        await tenant_repo.create(tenant)
        await session.commit()

        await status_service.transition("tenant-a", "BOOTSTRAPPING")
        await status_service.transition("tenant-a", "READY")
        await session.commit()

        history = await history_repo.list_for_tenant("tenant-a")
        statuses = [item.to_status for item in history]
        assert "BOOTSTRAPPING" in statuses
        assert "READY" in statuses
