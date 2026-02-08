
# AIOps PR Autopilot (safe automation)

## Safety rules
- AI never runs kubectl in prod.
- AI never outputs secrets.
- AI only proposes PRs to allowed paths and allowlisted fix types.

## EvidencePack and Proposal
- EvidencePack schema: schemas/evidence_pack.schema.json
- Proposal schema: schemas/ai_remediation_proposal.schema.json

## Fix-type allowlist (MVP)
- RESOURCE_TUNE
- HPA_TUNE
- CONFIG_FIX (deterministic only)
- ROLLBACK
- REDEPLOY (declarative)
- IMAGE_TAG_FIX

## Gating and approvals
- CI checks required (lint + render + policy checks)
- Approvals required based on risk_level and tenant policy
- PR bot must refuse actions outside allowlist

## Git provider abstraction
PR bot must use GitProviderAdapter; do not hardcode GitHub/GitLab.
