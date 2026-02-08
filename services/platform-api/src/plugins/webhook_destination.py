from __future__ import annotations

from typing import Dict, Any

import httpx

from adapters.interfaces import WebhookDeliveryResult, WebhookDestinationAdapter


class GenericWebhookDestinationAdapter(WebhookDestinationAdapter):
    def __init__(self, platform_config=None, client: httpx.Client | None = None) -> None:
        timeout = 10.0
        if platform_config:
            cfg = (platform_config.integrations or {}) if hasattr(platform_config, "integrations") else {}
            timeout = float(cfg.get("timeout_seconds", timeout))
        self._client = client or httpx.Client(timeout=timeout)

    def send(self, url: str, payload: Dict[str, Any], headers: Dict[str, str] | None = None) -> WebhookDeliveryResult:
        response = self._client.post(url, json=payload, headers=headers)
        if response.status_code >= 400:
            return WebhookDeliveryResult(status="failed", detail={"status_code": response.status_code, "body": response.text})
        return WebhookDeliveryResult(status="sent", detail={"status_code": response.status_code})
