from __future__ import annotations

import json
from pathlib import Path
import sys

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from main import create_app


ROOT = Path(__file__).resolve().parents[3]
SDK_PY = ROOT / "sdk" / "python" / "aiops_platform_client"
SDK_TS = ROOT / "sdk" / "typescript" / "src"


def _method_name(verb: str, path: str) -> str:
    clean = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    return f"{verb.lower()}_{clean}".replace("-", "_")


def _collect_operations(spec: dict) -> list[tuple[str, str]]:
    ops: list[tuple[str, str]] = []
    for path, methods in spec.get("paths", {}).items():
        if not path.startswith("/api/v1/"):
            continue
        for verb in methods.keys():
            if verb.lower() not in {"get", "post", "put", "delete", "patch"}:
                continue
            ops.append((verb.upper(), path))
    return sorted(set(ops))


def _emit_python(spec: dict) -> None:
    SDK_PY.mkdir(parents=True, exist_ok=True)
    operations = _collect_operations(spec)
    lines = [
        "from __future__ import annotations",
        "",
        "from typing import Any",
        "import requests",
        "",
        "",
        "class AIOpsClient:",
        "    def __init__(self, base_url: str, token: str | None = None, timeout: int = 30) -> None:",
        "        self.base_url = base_url.rstrip('/')",
        "        self.token = token",
        "        self.timeout = timeout",
        "",
        "    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:",
        "        headers = {'Content-Type': 'application/json'}",
        "        if self.token:",
        "            headers['Authorization'] = f'Bearer {self.token}'",
        "        resp = requests.request(method, f\"{self.base_url}{path}\", headers=headers, json=payload, timeout=self.timeout)",
        "        resp.raise_for_status()",
        "        return resp.json() if resp.text else None",
        "",
    ]
    for verb, path in operations:
        method_name = _method_name(verb, path)
        lines.extend(
            [
                f"    def {method_name}(self, payload: dict[str, Any] | None = None) -> Any:",
                f"        return self._request('{verb}', '{path}', payload=payload)",
                "",
            ]
        )
    (SDK_PY / "client.py").write_text("\n".join(lines), encoding="utf-8")
    (SDK_PY / "__init__.py").write_text("from .client import AIOpsClient\n", encoding="utf-8")
    (ROOT / "sdk" / "python" / "README.md").write_text(
        "# Python SDK\n\nGenerated from `services/platform-api` OpenAPI.\n",
        encoding="utf-8",
    )


def _emit_typescript(spec: dict) -> None:
    SDK_TS.mkdir(parents=True, exist_ok=True)
    operations = _collect_operations(spec)
    lines = [
        "export class AIOpsClient {",
        "  constructor(private readonly baseUrl: string, private readonly token?: string) {}",
        "",
        "  private async request(method: string, path: string, payload?: unknown): Promise<unknown> {",
        "    const headers: Record<string, string> = { 'Content-Type': 'application/json' };",
        "    if (this.token) headers['Authorization'] = `Bearer ${this.token}`;",
        "    const res = await fetch(`${this.baseUrl.replace(/\\/$/, '')}${path}`, {",
        "      method,",
        "      headers,",
        "      body: payload ? JSON.stringify(payload) : undefined,",
        "    });",
        "    if (!res.ok) throw new Error(`HTTP ${res.status}`);",
        "    return res.text().then((t) => (t ? JSON.parse(t) : null));",
        "  }",
        "",
    ]
    for verb, path in operations:
        method_name = _method_name(verb, path)
        lines.extend(
            [
                f"  async {method_name}(payload?: unknown): Promise<unknown> {{",
                f"    return this.request('{verb}', '{path}', payload);",
                "  }",
                "",
            ]
        )
    lines.append("}")
    (SDK_TS / "client.ts").write_text("\n".join(lines), encoding="utf-8")
    (ROOT / "sdk" / "typescript" / "README.md").write_text(
        "# TypeScript SDK\n\nGenerated from `services/platform-api` OpenAPI.\n",
        encoding="utf-8",
    )


def main() -> None:
    app = create_app()
    spec = app.openapi()
    openapi_out = ROOT / "sdk" / "openapi.json"
    openapi_out.parent.mkdir(parents=True, exist_ok=True)
    openapi_out.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    _emit_python(spec)
    _emit_typescript(spec)


if __name__ == "__main__":
    main()
