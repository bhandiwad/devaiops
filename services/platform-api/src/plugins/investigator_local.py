from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from adapters.interfaces import InvestigatorAdapter
from aiops.investigator import RuleBasedInvestigator
from config.loader import ConfigLoader
from config.validator import SchemaValidator


@dataclass
class LocalModelConfig:
    base_url: str
    model: str
    max_prompt_chars: int
    allowlist_fix_types: list[str]


class LocalModelInvestigator(InvestigatorAdapter):
    """Local model investigator using Ollama-compatible API."""

    def __init__(self, platform_config=None, client: Optional[httpx.Client] = None) -> None:
        if not platform_config:
            raise RuntimeError("PlatformConfig is required")
        aiops_cfg = platform_config.aiops or {}
        local_cfg = aiops_cfg.get("local_model") or {}
        allowlist = aiops_cfg.get("allowlist_fix_types") or []
        max_chars = aiops_cfg.get("max_prompt_chars")
        if not local_cfg.get("base_url") or not local_cfg.get("model") or not max_chars:
            raise RuntimeError("aiops.local_model.base_url, aiops.local_model.model, and aiops.max_prompt_chars are required")
        self._config = LocalModelConfig(
            base_url=local_cfg.get("base_url"),
            model=local_cfg.get("model"),
            max_prompt_chars=max_chars,
            allowlist_fix_types=allowlist,
        )
        self._client = client or httpx.Client(timeout=30.0)
        loader = ConfigLoader()
        self._repo_root = loader.repo_root
        self._schema_validator = SchemaValidator(loader.repo_root / "schemas")
        self._fallback = RuleBasedInvestigator(platform_config=platform_config)

    def _build_prompt(self, evidence_pack: Dict[str, Any]) -> str:
        payload = json.dumps(evidence_pack, default=str)
        truncated = payload[: self._config.max_prompt_chars]
        return "\n".join(
            [
                "You are an incident investigator. Output ONLY strict JSON matching the schema.",
                "Schema fields: summary, likely_root_cause, confidence (0-1), fix_type, risk_level (low|medium|high), validation_steps (array), rollback_plan, evidence_refs.",
                f"Allowed fix types: {', '.join(self._config.allowlist_fix_types)}",
                "Evidence:",
                truncated,
            ]
        )

    def _call_model(self, prompt: str) -> str:
        response = self._client.post(
            f"{self._config.base_url.rstrip('/')}/api/generate",
            json={"model": self._config.model, "prompt": prompt, "stream": False},
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Local model error {response.status_code}: {response.text}")
        data = response.json()
        return data.get("response", "")

    def investigate(self, evidence_pack: Dict[str, Any]) -> Dict[str, Any]:
        self.last_fallback = False
        prompt = self._build_prompt(evidence_pack)
        try:
            raw = self._call_model(prompt)
            proposal = json.loads(raw)
            if proposal.get("fix_type") not in self._config.allowlist_fix_types:
                raise RuntimeError("Fix type not allowlisted")
            self._schema_validator.validate(
                "ai_remediation_proposal.schema.json",
                proposal,
                self._repo_root / "schemas" / "ai_remediation_proposal.schema.json",
            )
            return proposal
        except Exception:
            self.last_fallback = True
            return self._fallback.investigate(evidence_pack)

    def health(self) -> Dict[str, Any]:
        try:
            response = self._client.get(f"{self._config.base_url.rstrip('/')}/api/tags")
            if response.status_code >= 400:
                return {"status": "unhealthy"}
            return {"status": "ok"}
        except Exception:
            return {"status": "unhealthy"}
