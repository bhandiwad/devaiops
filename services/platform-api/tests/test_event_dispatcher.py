from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from integrations.event_dispatcher import EventDispatcher


@dataclass
class _Event:
    event_id: str
    tenant_id: str | None
    type: str
    payload: dict
    status: str = "PENDING"
    dispatched_at: object | None = None


@dataclass
class _Sub:
    subscription_id: str
    tenant_id: str | None
    event_types: list[str]
    destination_ref: str
    headers_ref: str | None = None
    status: str = "ACTIVE"


class _EventRepo:
    def __init__(self, events):
        self.events = events
        self.updated: list[_Event] = []

    async def list_pending(self, limit: int = 100):
        return self.events[:limit]

    async def update(self, event):
        self.updated.append(event)
        return event


class _SubRepo:
    def __init__(self, tenant_subs=None, global_subs=None):
        self._tenant_subs = tenant_subs or []
        self._global_subs = global_subs or []

    async def list_for_tenant(self, tenant_id: str):
        return self._tenant_subs

    async def list_global(self):
        return self._global_subs


class _Webhook:
    def __init__(self, fail_url: str | None = None):
        self.calls: list[tuple[str, dict, dict | None]] = []
        self.fail_url = fail_url

    def send(self, url: str, payload: dict, headers: dict | None = None):
        self.calls.append((url, payload, headers))
        if self.fail_url and url == self.fail_url:
            return SimpleNamespace(status="failed")
        return SimpleNamespace(status="sent")


class _Secrets:
    def read_secret(self, ref: str):
        if ref == "vault://headers":
            return {"X-Test": "ok"}
        return {}


class _Registry:
    def __init__(self, webhook):
        self._webhook = webhook

    def webhook_destination(self):
        return self._webhook

    def secrets(self):
        return _Secrets()


@pytest.mark.asyncio
async def test_event_dispatcher_delivers_and_marks_dispatched():
    event = _Event(event_id="evt-1", tenant_id="t-1", type="IncidentCreated", payload={"x": 1})
    sub_repo = _SubRepo(
        tenant_subs=[_Sub(subscription_id="s1", tenant_id="t-1", event_types=["IncidentCreated"], destination_ref="https://a")],
        global_subs=[_Sub(subscription_id="s2", tenant_id=None, event_types=["*"], destination_ref="https://b", headers_ref="vault://headers")],
    )
    event_repo = _EventRepo([event])
    webhook = _Webhook()
    dispatcher = EventDispatcher(_Registry(webhook), event_repo, sub_repo)
    summary = await dispatcher.dispatch_pending(limit=10)
    assert summary.delivered == 1
    assert summary.failed == 0
    assert event.status == "DISPATCHED"
    assert len(webhook.calls) == 2
    assert webhook.calls[1][2] == {"X-Test": "ok"}


@pytest.mark.asyncio
async def test_event_dispatcher_marks_retryable_on_delivery_failure():
    event = _Event(event_id="evt-2", tenant_id="t-1", type="IncidentCreated", payload={})
    sub_repo = _SubRepo(tenant_subs=[_Sub(subscription_id="s1", tenant_id="t-1", event_types=["*"], destination_ref="https://fail")])
    event_repo = _EventRepo([event])
    webhook = _Webhook(fail_url="https://fail")
    dispatcher = EventDispatcher(_Registry(webhook), event_repo, sub_repo)
    summary = await dispatcher.dispatch_pending(limit=10)
    assert summary.delivered == 0
    assert summary.failed == 1
    assert event.status == "FAILED_RETRYABLE"
