from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from adapters.registry import AdapterRegistry
from db.models import Event
from db.repositories import EventRepository, SubscriptionRepository


@dataclass
class DispatchSummary:
    delivered: int = 0
    failed: int = 0


class EventDispatcher:
    def __init__(
        self,
        registry: AdapterRegistry,
        event_repo: EventRepository,
        subscription_repo: SubscriptionRepository,
    ) -> None:
        self._registry = registry
        self._event_repo = event_repo
        self._subscription_repo = subscription_repo

    async def dispatch_pending(self, limit: int = 100) -> DispatchSummary:
        summary = DispatchSummary()
        events = await self._event_repo.list_pending(limit=limit)
        for event in events:
            subscriptions = await self._resolve_subscriptions(event)
            ok = True
            for sub in subscriptions:
                headers = await self._resolve_headers(sub.headers_ref)
                result = self._registry.webhook_destination().send(
                    url=sub.destination_ref,
                    payload={"event_type": event.type, "event_id": event.event_id, "payload": event.payload},
                    headers=headers,
                )
                if result.status != "sent":
                    ok = False
            event.status = "DISPATCHED" if ok else "FAILED_RETRYABLE"
            event.dispatched_at = datetime.now(timezone.utc)
            await self._event_repo.update(event)
            if ok:
                summary.delivered += 1
            else:
                summary.failed += 1
        return summary

    async def _resolve_subscriptions(self, event: Event):
        tenant_subs = await self._subscription_repo.list_for_tenant(event.tenant_id) if event.tenant_id else []
        global_subs = await self._subscription_repo.list_global()
        matched = []
        for sub in [*tenant_subs, *global_subs]:
            event_types = sub.event_types or []
            if not event_types or event.type in event_types or "*" in event_types:
                matched.append(sub)
        return matched

    async def _resolve_headers(self, headers_ref: str | None) -> dict[str, str] | None:
        if not headers_ref:
            return None
        secrets = self._registry.secrets()
        resolved = secrets.read_secret(headers_ref)
        return {str(k): str(v) for k, v in resolved.items()}
