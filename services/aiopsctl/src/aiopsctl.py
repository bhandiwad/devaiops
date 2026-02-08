from __future__ import annotations

import argparse
import json
import os
import sys

import requests


API_BASE = os.getenv("AIOPS_API_BASE", "http://localhost:8000")
API_PREFIX = "/api/v1"
TOKEN = os.getenv("AIOPS_TOKEN", "")


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    return headers


def _request(method: str, path: str, payload: dict | None = None):
    url = f"{API_BASE}{API_PREFIX}{path}"
    resp = requests.request(method, url, headers=_headers(), json=payload, timeout=30)
    if resp.status_code >= 400:
        raise SystemExit(f"HTTP {resp.status_code}: {resp.text}")
    if resp.text:
        print(json.dumps(resp.json(), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(prog="aiopsctl")
    sub = parser.add_subparsers(dest="command", required=True)

    scaffold = sub.add_parser("scaffold")
    scaffold.add_argument("tenant_id")
    scaffold.add_argument("template_id")
    scaffold.add_argument("service_name")
    scaffold.add_argument("owner")

    promote = sub.add_parser("promote")
    promote.add_argument("tenant_id")
    promote.add_argument("service_id")
    promote.add_argument("from_env")
    promote.add_argument("to_env")

    products = sub.add_parser("products")
    products_sub = products.add_subparsers(dest="products_cmd", required=True)
    products_sub.add_parser("list")
    p_enable = products_sub.add_parser("enable")
    p_enable.add_argument("tenant_id")
    p_enable.add_argument("product_id")
    p_disable = products_sub.add_parser("disable")
    p_disable.add_argument("tenant_id")
    p_disable.add_argument("product_id")

    access = sub.add_parser("access")
    access_sub = access.add_subparsers(dest="access_cmd", required=True)
    a_req = access_sub.add_parser("request")
    a_req.add_argument("tenant_id")
    a_req.add_argument("role")
    a_ap = access_sub.add_parser("approve")
    a_ap.add_argument("tenant_id")
    a_ap.add_argument("request_id")
    a_dn = access_sub.add_parser("deny")
    a_dn.add_argument("tenant_id")
    a_dn.add_argument("request_id")

    subscriptions = sub.add_parser("subscriptions")
    subscriptions_sub = subscriptions.add_subparsers(dest="subscriptions_cmd", required=True)
    s_list = subscriptions_sub.add_parser("list")
    s_list.add_argument("tenant_id")
    s_create = subscriptions_sub.add_parser("create")
    s_create.add_argument("tenant_id")
    s_create.add_argument("destination_ref")
    s_create.add_argument("event_types")
    s_delete = subscriptions_sub.add_parser("delete")
    s_delete.add_argument("tenant_id")
    s_delete.add_argument("subscription_id")

    incidents = sub.add_parser("incidents")
    incidents_sub = incidents.add_subparsers(dest="incidents_cmd", required=True)
    i_notify = incidents_sub.add_parser("notify")
    i_notify.add_argument("tenant_id")
    i_notify.add_argument("incident_id")
    i_notify.add_argument("--message", default=None)
    i_ticket = incidents_sub.add_parser("create-ticket")
    i_ticket.add_argument("tenant_id")
    i_ticket.add_argument("incident_id")
    i_ticket.add_argument("--title", default=None)

    args = parser.parse_args()

    if args.command == "scaffold":
        _request(
            "POST",
            f"/tenants/{args.tenant_id}/scaffold",
            {
                "template_id": args.template_id,
                "parameters": {"service_name": args.service_name, "owner": args.owner},
            },
        )
    elif args.command == "promote":
        _request(
            "POST",
            f"/tenants/{args.tenant_id}/services/{args.service_id}/promote?from_env={args.from_env}&to_env={args.to_env}",
        )
    elif args.command == "products":
        if args.products_cmd == "list":
            _request("GET", "/products")
        elif args.products_cmd == "enable":
            _request("POST", f"/tenants/{args.tenant_id}/products/{args.product_id}/enable")
        elif args.products_cmd == "disable":
            _request("POST", f"/tenants/{args.tenant_id}/products/{args.product_id}/disable")
    elif args.command == "access":
        if args.access_cmd == "request":
            _request("POST", f"/tenants/{args.tenant_id}/access/requests", {"requested_role": args.role})
        elif args.access_cmd == "approve":
            _request("POST", f"/tenants/{args.tenant_id}/access/requests/{args.request_id}/approve")
        elif args.access_cmd == "deny":
            _request("POST", f"/tenants/{args.tenant_id}/access/requests/{args.request_id}/deny")
    elif args.command == "subscriptions":
        if args.subscriptions_cmd == "list":
            _request("GET", f"/tenants/{args.tenant_id}/subscriptions")
        elif args.subscriptions_cmd == "create":
            _request(
                "POST",
                f"/tenants/{args.tenant_id}/subscriptions",
                {"destination_ref": args.destination_ref, "event_types": [e.strip() for e in args.event_types.split(",") if e.strip()]},
            )
        elif args.subscriptions_cmd == "delete":
            _request("DELETE", f"/tenants/{args.tenant_id}/subscriptions/{args.subscription_id}")
    elif args.command == "incidents":
        if args.incidents_cmd == "notify":
            payload = {"message": args.message} if args.message else {}
            _request("POST", f"/tenants/{args.tenant_id}/incidents/{args.incident_id}/notify", payload)
        elif args.incidents_cmd == "create-ticket":
            payload = {"title": args.title} if args.title else {}
            _request("POST", f"/tenants/{args.tenant_id}/incidents/{args.incident_id}/create-ticket", payload)


if __name__ == "__main__":
    main()
