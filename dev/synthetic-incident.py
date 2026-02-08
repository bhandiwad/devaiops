from __future__ import annotations

import argparse
import json
import os
import uuid

import requests


def headers() -> dict[str, str]:
    token = os.getenv("AIOPS_TOKEN", "")
    if token:
        return {"Content-Type": "application/json", "Authorization": f"Bearer {token}"}
    return {
        "Content-Type": "application/json",
        "X-Dev-Principal": json.dumps(
            {
                "principal_id": "demo-incident",
                "email": "demo@example.com",
                "realm_roles": ["platform_admin"],
                "tenant_roles": {},
            }
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--service", default="payments")
    parser.add_argument("--api", default=os.getenv("AIOPS_API_BASE", "http://localhost:8000"))
    args = parser.parse_args()

    payload = {
        "alert_name": "SyntheticCrashLoopBackOff",
        "service_id": args.service,
        "alert": {
            "id": str(uuid.uuid4()),
            "severity": "warning",
            "labels": {"tenant_id": args.tenant, "service": args.service},
            "annotations": {"summary": "Synthetic incident for beta validation"},
        },
    }
    r = requests.post(f"{args.api}/api/v1/tenants/{args.tenant}/incidents", headers=headers(), json=payload, timeout=30)
    r.raise_for_status()
    print(json.dumps(r.json(), indent=2))


if __name__ == "__main__":
    main()
