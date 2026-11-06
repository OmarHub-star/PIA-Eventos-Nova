from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.application.security import Principal
from src.infrastructure.database import SqlUnitOfWork, make_engine, metadata
from src.infrastructure.fixtures import seed

TOKENS = {
    "admin-test": {"id": "ADM-001", "role": "ADMIN"},
    "coord-test": {"id": "COORD-001", "role": "COORDINADOR"},
    "client-test": {"id": "EVE-C001", "role": "CLIENTE"},
    "other-test": {"id": "EVE-C002", "role": "CLIENTE"},
    "supplier-test": {"id": "PROV-001", "role": "PROVEEDOR"},
    "backup-test": {"id": "PROV-002", "role": "PROVEEDOR"},
}


class FixedClock:
    def __init__(self):
        self.value = datetime(2026, 11, 6, 18, tzinfo=timezone.utc)

    def now(self):
        return self.value


@pytest.fixture
def clock():
    return FixedClock()


@pytest.fixture
def client(tmp_path, clock):
    app = create_app(
        "sqlite:///" + str(tmp_path / "api.db"), tokens=TOKENS, clock=clock, seed_data=True
    )
    with TestClient(app) as client:
        yield client


def auth(role="coord"):
    return {"Authorization": "Bearer " + role + "-test"}


def payload(event_id="DEMO-001", day="2026-12-06"):
    return {
        "id": event_id,
        "client_id": "EVE-C001",
        "event_date": day,
        "title": "Boda demostración",
        "guests": 100,
        "items": [{"resource_id": "EVE-P001", "quantity": 10}],
    }


def call(client, event_id, action, data=None, role="coord"):
    return client.post(f"/events/{event_id}/{action}", json=data or {}, headers=auth(role))


def confirmed(client, event_id="DEMO-001", day="2026-12-06"):
    response = client.post("/events", json=payload(event_id, day), headers=auth())
    assert response.status_code == 201, response.text
    assert call(client, event_id, "send").status_code == 200
    assert call(client, event_id, "accept", role="client").status_code == 200
    assert call(client, event_id, "sign", {"reference": "CONTRATO-01"}, "client").status_code == 200
    response = call(
        client,
        event_id,
        "pay",
        {"amount": "1767.00", "reference": "ANTICIPO-01", "method": "TRANSFERENCIA"},
        "admin",
    )
    assert response.status_code == 200, response.text
    return response.json()


def assign(client, event_id="DEMO-001", supplier="PROV-001", **extra):
    return client.post(
        f"/events/{event_id}/requests",
        headers=auth(),
        json={"supplier_id": supplier, "service": "Banquete", "cost": "1000.00", **extra},
    )


@pytest.fixture
def database(tmp_path):
    engine = make_engine("sqlite:///" + str(tmp_path / "nova.db"))
    metadata.create_all(engine)

    def factory():
        return SqlUnitOfWork(engine)

    seed(factory)
    yield factory
    engine.dispose()


@pytest.fixture
def coordinator():
    return Principal("COORD-001", "COORDINADOR")
