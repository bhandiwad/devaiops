
# Configuration system

## 1) Sources and precedence
Recommended precedence:
1) Environment variables (secrets and runtime overrides)
2) TenantSpec (tenant-level)
3) ProviderProfile (environment-level)
4) PlatformConfig (global)

## 2) Storage model
- Configs live in a Git repo (recommended) or a mounted filesystem.
- Secrets are never stored in config repo; use Vault or env injection.

## 3) Validation
- All configs must validate against schemas in /schemas.
- Platform API rejects invalid config at load time and on write.

## 4) Config reload strategy
- Platform API supports hot-reload on config repo change (polling/webhook).
- Any change triggers:
  - schema validation
  - impact analysis (which tenants/modules are affected)
  - optional “plan” output before apply

## 5) “No hardcoded defaults” enforcement
- Any default used by code must come from PlatformConfig.
- ProviderProfile overrides PlatformConfig.
- TenantSpec overrides ProviderProfile.
