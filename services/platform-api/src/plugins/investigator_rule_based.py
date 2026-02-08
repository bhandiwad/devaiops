from __future__ import annotations

from aiops.investigator import RuleBasedInvestigator


class RuleBasedInvestigatorAdapter(RuleBasedInvestigator):
    """Rule-based investigator adapter (fallback)."""

    def __init__(self, platform_config=None):
        super().__init__(platform_config=platform_config)
