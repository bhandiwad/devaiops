
# Unified CLI: aiopsctl

## Goals
- Single CLI for platform and tenant operations.
- Uses Keycloak OIDC for auth.
- Calls Platform API only.
- Respects RBAC identically to UI.

## Commands (minimum)
- aiopsctl login
- aiopsctl me
- aiopsctl profiles list|get
- aiopsctl modules list|get
- aiopsctl tenant create|list|get|upgrade|delete
- aiopsctl service create|list|get
- aiopsctl deploy status|rollback
- aiopsctl incident list|get|investigate|create-pr
- aiopsctl access grant|revoke|list
- aiopsctl audit tail
- aiopsctl scaffold service ...
- aiopsctl promote ...
- aiopsctl products list|enable|disable
- aiopsctl access request|approve|deny

## Implementation recommendation
- Python: typer + httpx
- Keycloak device-code flow preferred for CLI usability

Current implementation in this repo is a thin API-only CLI under `services/aiopsctl` using Python argparse + requests.
