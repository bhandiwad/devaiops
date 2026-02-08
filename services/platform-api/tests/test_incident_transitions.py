from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.routes import _record_incident_transition
from db.models import Base, Incident
from db.repositories import IncidentTransitionRepository


@pytest.mark.asyncio
async def test_incident_transition_happy_path():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        incident = Incident(
            incident_id="inc-1",
            tenant_id="t-1",
            service_id="svc",
            alert_name="HighErrorRate",
            status="NEW",
            alert_json={},
            evidence_json={},
            proposal_json={},
        )
        session.add(incident)
        await session.flush()
        transition = await _record_incident_transition(session, "t-1", incident, "EVIDENCE_COLLECTED")
        await session.commit()
        assert transition.from_status == "NEW"
        assert transition.to_status == "EVIDENCE_COLLECTED"
        history = await IncidentTransitionRepository(session).list_for_incident("inc-1")
        assert len(history) == 1


@pytest.mark.asyncio
async def test_incident_transition_invalid_path():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        incident = Incident(
            incident_id="inc-2",
            tenant_id="t-1",
            service_id="svc",
            alert_name="HighErrorRate",
            status="NEW",
            alert_json={},
            evidence_json={},
            proposal_json={},
        )
        session.add(incident)
        await session.flush()
        with pytest.raises(HTTPException):
            await _record_incident_transition(session, "t-1", incident, "RESOLVED")
