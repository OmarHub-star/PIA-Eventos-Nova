"""Crea configuración local sin sobreescribir un archivo existente."""

import json
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT / ".env"
    if path.exists():
        print(".env ya existe. Se conserva su configuración.")
        return
    users = [
        ("ADM-001", "ADMIN"),
        ("COORD-001", "COORDINADOR"),
        ("EVE-C001", "CLIENTE"),
        ("PROV-001", "PROVEEDOR"),
        ("PROV-002", "PROVEEDOR"),
    ]
    tokens = {
        secrets.token_urlsafe(32): {"id": entity_id, "role": role} for entity_id, role in users
    }
    content = "DATABASE_URL=sqlite:///./nova.db\nSEED_DATA=true\nPORT=8000\nPOSTGRES_USER=nova\nPOSTGRES_DB=nova\n"
    content += "POSTGRES_PASSWORD=" + secrets.token_hex(24) + "\n"
    content += "TOKENS_JSON=" + json.dumps(tokens, separators=(",", ":")) + "\n"
    path.write_text(content, encoding="utf-8")
    path.chmod(0o600)
    print("Configuración creada en .env. Usa sus tokens en Authorize de /docs.")


if __name__ == "__main__":
    main()
