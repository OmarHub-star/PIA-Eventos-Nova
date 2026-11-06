"""Se ejecuta con PostgreSQL/Compose en CI. Se informa SKIP si no hay servicios."""

import os
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import delete

from src.infrastructure.database import SqlUnitOfWork, documents, make_engine, metadata


@pytest.mark.skipif(
    not os.getenv("TEST_DATABASE_URL"), reason="PostgreSQL no configurado en este entorno"
)
def test_postgresql_real_commit_rollback():
    engine = make_engine(os.environ["TEST_DATABASE_URL"])
    metadata.create_all(engine)
    entity_id = "PG-" + str(uuid4())
    try:
        with SqlUnitOfWork(engine) as uow:
            uow.save("test", entity_id, {"id": entity_id, "value": "committed"})
            uow.commit()
        with SqlUnitOfWork(engine) as uow:
            assert uow.get("test", entity_id)["value"] == "committed"
            uow.save("test", entity_id, {"id": entity_id, "value": "rollback"})
        with SqlUnitOfWork(engine) as uow:
            assert uow.get("test", entity_id)["value"] == "committed"
    finally:
        with engine.begin() as connection:
            connection.execute(
                delete(documents).where(documents.c.kind == "test", documents.c.id == entity_id)
            )
        engine.dispose()


@pytest.mark.skipif(
    not os.getenv("API_BASE_URL"), reason="API externa no configurada en este entorno"
)
def test_real_http_service_health_and_OpenAPI():
    base = os.environ["API_BASE_URL"].rstrip("/")
    assert httpx.get(base + "/health", timeout=10, trust_env=False).json()["status"] == "ok"
    assert (
        "/events" in httpx.get(base + "/openapi.json", timeout=10, trust_env=False).json()["paths"]
    )
