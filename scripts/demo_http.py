"""Recorrido HTTP reproducible con cinco roles y registro sin credenciales."""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--output", default=str(ROOT / "docs/evidencias/demo_http.json"))
    args = parser.parse_args()
    config = {}
    if (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                config[key] = value
    tokens = json.loads(os.getenv("TOKENS_JSON", config.get("TOKENS_JSON", "{}")))
    identities = {p["id"]: token for token, p in tokens.items()}
    roles = {p["role"]: token for token, p in tokens.items() if p["role"] != "PROVEEDOR"}
    roles["CLIENTE"] = identities["EVE-C001"]
    roles["PROVEEDOR"] = identities["PROV-001"]
    logs = []
    event_id = "DEMO-" + uuid4().hex[:10]

    with httpx.Client(base_url=args.base_url, timeout=20, trust_env=False) as client:

        def request(method, path, role, body=None, expected=200):
            response = client.request(
                method, path, json=body, headers={"Authorization": "Bearer " + roles[role]}
            )
            value = response.json()
            logs.append(
                {
                    "method": method,
                    "path": path,
                    "role": role,
                    "status": response.status_code,
                    "expected": expected,
                    "result": {
                        k: v
                        for k, v in value.items()
                        if k
                        in {
                            "id",
                            "state",
                            "total",
                            "balance",
                            "paid",
                            "detail",
                            "margin",
                            "income",
                            "supplier_cost",
                            "extra_id",
                            "change_id",
                        }
                    },
                }
            )
            if response.status_code != expected:
                raise RuntimeError(
                    f"{path}: se esperaba {expected}, se obtuvo {response.status_code}: {value}"
                )
            return value

        def action(name, role="COORDINADOR", body=None, expected=200):
            return request("POST", f"/events/{event_id}/{name}", role, body or {}, expected)

        today = datetime.now(ZoneInfo("America/Mexico_City")).date().isoformat()
        request(
            "POST",
            "/events",
            "COORDINADOR",
            {
                "id": event_id,
                "client_id": "EVE-C001",
                "event_date": today,
                "title": "Demostración PIA",
                "guests": 100,
                "items": [{"resource_id": "EVE-P001", "quantity": 10}],
            },
            201,
        )
        action("send")
        action("accept", "CLIENTE")
        action("accept", "CLIENTE", expected=409)
        action("sign", "CLIENTE", {"reference": "CONTRATO-DEMO"})
        action(
            "pay",
            "ADMIN",
            {"amount": "1767.00", "reference": "ANTICIPO-DEMO", "method": "TRANSFERENCIA"},
        )
        supplier = request(
            "POST",
            f"/events/{event_id}/requests",
            "COORDINADOR",
            {"supplier_id": "PROV-001", "service": "Banquete", "cost": "1000.00"},
            201,
        )
        request("POST", f"/requests/{supplier['id']}/respond", "PROVEEDOR", {"accepted": True})
        change = action("change", body={"guests": 110, "increment": "100.00"})
        action("approve", "ADMIN", {"change_id": change["change_id"]})
        action("start")
        extra = action("extra", body={"description": "Música adicional", "amount": "100.00"})
        action("deliver_extra", body={"extra_id": extra["extra_id"]}, expected=422)
        action(
            "pay_extra",
            "ADMIN",
            {"extra_id": extra["extra_id"], "reference": "EXTRA-DEMO", "method": "TERMINAL"},
        )
        action("deliver_extra", body={"extra_id": extra["extra_id"]})
        finished = action("finish")
        action("close", body={"act": "Intento con saldo"}, expected=422)
        action(
            "pay",
            "ADMIN",
            {
                "amount": finished["balance"],
                "reference": "LIQUIDACION-DEMO",
                "method": "TRANSFERENCIA",
            },
        )
        action("close", body={"act": "ACTA-DEMO. Servicio recibido a satisfacción."})
        request("GET", f"/events/{event_id}/profitability", "ADMIN")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "executed_at": datetime.now(ZoneInfo("America/Mexico_City")).isoformat(),
                "base_url": args.base_url,
                "event_id": event_id,
                "steps": logs,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"{len(logs)} peticiones verificadas. Evento {event_id} cerrado. Evidencia: {output.name}"
    )


if __name__ == "__main__":
    main()
