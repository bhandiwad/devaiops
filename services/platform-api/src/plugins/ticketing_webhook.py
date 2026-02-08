from __future__ import annotations

from typing import Dict, Any

from adapters.interfaces import TicketRef, TicketingAdapter


class GenericTicketingAdapter(TicketingAdapter):
    def create_ticket(self, tenant_id: str, payload: Dict[str, Any]) -> TicketRef:
        key = payload.get("external_key", f"TICKET-{tenant_id}-001")
        return TicketRef(ticket_id=key, url=payload.get("url"), metadata={"created": True, "payload": payload})

    def update_ticket(self, ticket_ref: TicketRef, payload: Dict[str, Any]) -> TicketRef:
        merged = dict(ticket_ref.metadata)
        merged.update({"updated": True, "payload": payload})
        return TicketRef(ticket_id=ticket_ref.ticket_id, url=ticket_ref.url, metadata=merged)
