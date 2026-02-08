from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from adapters.interfaces import InvestigatorAdapter
from config.loader import ConfigLoader
from config.validator import SchemaValidator


@dataclass
class InvestigationResult:
    proposal: Dict[str, Any]


class RuleBasedInvestigator(InvestigatorAdapter):
    def __init__(self, platform_config=None):
        loader = ConfigLoader()
        self.validator = SchemaValidator(loader.repo_root / "schemas")
        self.repo_root = loader.repo_root

    def _find_pod_reasons(self, evidence: Dict[str, Any]) -> List[str]:
        reasons = []
        for resource in evidence.get("k8s", {}).get("snapshot", []):
            status = resource.get("status", {})
            for cs in status.get("container_statuses", []) or []:
                waiting = (cs.get("state") or {}).get("waiting")
                if waiting and waiting.get("reason"):
                    reasons.append(waiting["reason"])
                last_state = (cs.get("last_state") or {}).get("terminated")
                if last_state and last_state.get("reason"):
                    reasons.append(last_state["reason"])
        return reasons

    def investigate(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        reasons = self._find_pod_reasons(evidence)
        fix_type = "ROLLBACK"
        risk = "medium"
        summary = "Rollback to last known good release."
        root_cause = "Unknown"
        confidence = 0.4
        validation_steps = ["Verify rollout stability", "Monitor error rate"]
        rollback_plan = "Revert to previous image/tag via GitOps."\

        if "CrashLoopBackOff" in reasons and "OOMKilled" in reasons:
            fix_type = "RESOURCE_TUNE"
            risk = "medium"
            summary = "Increase memory limits to address OOMKilled pods."
            root_cause = "Pods are OOMKilled under current limits."
            confidence = 0.7
            rollback_plan = "Revert resource limit changes in GitOps values."
        elif "ImagePullBackOff" in reasons or "ErrImagePull" in reasons:
            fix_type = "IMAGE_TAG_FIX"
            risk = "low"
            summary = "Update image tag or registry reference to a valid image."
            root_cause = "Image could not be pulled."
            confidence = 0.6
            rollback_plan = "Revert to previous image tag."
        elif "CrashLoopBackOff" in reasons:
            fix_type = "ROLLBACK"
            risk = "medium"
            summary = "Rollback to last known good deployment."
            root_cause = "Containers repeatedly crashing."
            confidence = 0.5

        proposal = {
            "summary": summary,
            "likely_root_cause": root_cause,
            "confidence": confidence,
            "fix_type": fix_type,
            "risk_level": risk,
            "validation_steps": validation_steps,
            "rollback_plan": rollback_plan,
            "evidence_refs": ["k8s.snapshot", "k8s.events", "logs", "metrics"],
        }

        self.validator.validate(
            "ai_remediation_proposal.schema.json",
            proposal,
            self.repo_root / "schemas" / "ai_remediation_proposal.schema.json",
        )
        return proposal

    def health(self) -> Dict[str, Any]:
        return {"status": "ok"}
