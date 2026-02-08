from __future__ import annotations

from typing import Dict, Any

from adapters.interfaces import MessageRef, MessagingAdapter


class WebhookMessagingAdapter(MessagingAdapter):
    def __init__(self, platform_config=None) -> None:
        self._cfg = (platform_config.integrations or {}) if platform_config and hasattr(platform_config, "integrations") else {}

    def post_message(self, tenant_id: str, payload: Dict[str, Any]) -> MessageRef:
        channel = payload.get("channel") or self._cfg.get("default_channel", "general")
        return MessageRef(message_id=f"msg-{tenant_id}-{channel}", metadata={"channel": channel, "payload": payload})
