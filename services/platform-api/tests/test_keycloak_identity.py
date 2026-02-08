import time

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from config.models import PlatformConfig
from plugins.keycloak import KeycloakIdentityAdapter


def _make_rsa_keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_key = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_key = key.public_key().public_numbers()
    return key, private_key, public_key


def test_keycloak_identity_adapter_validates_jwt():
    key, private_key, public = _make_rsa_keypair()
    jwk = {
        "kty": "RSA",
        "kid": "test",
        "use": "sig",
        "alg": "RS256",
        "n": jwt.utils.base64url_encode(public.n.to_bytes((public.n.bit_length() + 7) // 8, "big")).decode(),
        "e": jwt.utils.base64url_encode(public.e.to_bytes((public.e.bit_length() + 7) // 8, "big")).decode(),
    }

    def handler(request: httpx.Request):
        return httpx.Response(200, json={"keys": [jwk]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    platform_config = PlatformConfig.model_validate(
        {
            "modules": {"module_catalog_path": "config/module_catalog.yaml"},
            "identity": {
                "oidc": {
                    "issuer_url": "https://issuer.example/realms/demo",
                    "audience": "platform-api",
                    "jwks_url": "https://issuer.example/realms/demo/protocol/openid-connect/certs",
                },
                "claims": {
                    "tenant_roles_claim": "tenant_roles",
                    "realm_roles_claim": "realm_access.roles",
                    "subject_claim": "sub",
                    "email_claim": "email",
                },
                "jwks_cache_seconds": 300,
            },
            "adapters": {},
            "rbac": {},
        }
    )
    adapter = KeycloakIdentityAdapter(platform_config=platform_config, client=client)

    now = int(time.time())
    token = jwt.encode(
        {
            "sub": "user-1",
            "email": "user@example.com",
            "tenant_roles": {"tenant-a": ["tenant_viewer"]},
            "realm_access": {"roles": ["platform_admin"]},
            "iss": "https://issuer.example/realms/demo",
            "aud": "platform-api",
            "iat": now,
            "exp": now + 300,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test"},
    )
    principal = adapter.verify_token(token)
    context = adapter.get_context(principal)
    assert context.principal_id == "user-1"
    assert "platform_admin" in context.realm_roles
    assert "tenant-a" in context.tenant_roles
