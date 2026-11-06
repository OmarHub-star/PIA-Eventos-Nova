from datetime import datetime, timedelta, timezone

import pytest

from tests.conftest import assign, auth, call, confirmed, payload


def test_US01_US15_full_business_cycle(client, clock):
    data = confirmed(client, day="2026-11-06")
    assert data["state"] == "CONFIRMADO"
    assert data["balance"] == "4123.00"
    request = assign(client).json()
    response = client.post(
        f"/requests/{request['id']}/respond", json={"accepted": True}, headers=auth("supplier")
    )
    assert response.status_code == 200
    result = call(
        client,
        "DEMO-001",
        "pay",
        {"amount": "4123.00", "reference": "LIQUIDACION", "method": "TRANSFERENCIA"},
        "admin",
    )
    assert result.json()["balance"] == "0.00"
    assert call(client, "DEMO-001", "start").json()["state"] == "EN_EJECUCION"
    extra = call(
        client, "DEMO-001", "extra", {"description": "Música adicional", "amount": "100.00"}
    ).json()
    extra_id = extra["extra_id"]
    assert call(client, "DEMO-001", "deliver_extra", {"extra_id": extra_id}).status_code == 422
    assert (
        call(
            client,
            "DEMO-001",
            "pay_extra",
            {"extra_id": extra_id, "reference": "EXTRA-01", "method": "TERMINAL"},
            "admin",
        ).status_code
        == 200
    )
    assert call(client, "DEMO-001", "deliver_extra", {"extra_id": extra_id}).status_code == 200
    assert call(client, "DEMO-001", "finish").json()["state"] == "FINALIZADO"
    result = call(
        client, "DEMO-001", "close", {"act": "ACTA-001. Servicio entregado a satisfacción."}
    )
    assert result.json()["state"] == "CERRADO"
    assert call(client, "DEMO-001", "close", {"act": "REPETIDA"}).status_code == 409
    margin = client.get("/events/DEMO-001/profitability", headers=auth("admin")).json()
    assert margin["income"] == "5990.00"
    assert margin["supplier_cost"] == "1000.00"
    assert margin["margin"] == "4990.00"
    audit = client.get("/events/DEMO-001/audit", headers=auth()).json()
    assert any(row["name"] == "EventoCerrado" for row in audit)
    assert all(row["actor"] and row["at"] for row in audit)


def test_US07_revision_history_and_duplicate_accept(client):
    assert client.post("/events", json=payload(), headers=auth()).status_code == 201
    revision = call(
        client,
        "DEMO-001",
        "revise",
        {
            "items": [{"resource_id": "EVE-P001", "quantity": 11}],
            "reason": "Cliente solicita aforo mayor",
        },
    )
    assert revision.json()["proposal"]["versions"][0]["total"] == "5890.00"
    assert revision.json()["proposal"]["versions"][1]["total"] == "6479.00"
    assert call(client, "DEMO-001", "send").status_code == 200
    assert (
        call(
            client,
            "DEMO-001",
            "revise",
            {"items": [{"resource_id": "EVE-P001", "quantity": 1}], "reason": "Cambio"},
        ).status_code
        == 409
    )
    assert call(client, "DEMO-001", "accept", role="client").status_code == 200
    assert call(client, "DEMO-001", "accept", role="client").status_code == 409


@pytest.mark.parametrize(
    "days,late,charge", [(16, False, "0.00"), (15, False, "0.00"), (14, True, "15.00")]
)
def test_US08_US10_changes_authorization_and_notification(client, days, late, charge):
    day = (datetime(2026, 11, 6) + timedelta(days=days)).date().isoformat()
    confirmed(client, day=day)
    request = assign(client).json()
    response = call(client, "DEMO-001", "change", {"guests": 120, "increment": "100.00"})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["evaluation"]["charge"] == charge
    assert (result["changes"][0]["state"] == "PENDIENTE") is late
    if late:
        assert result["total"] == "5890.00"
        assert (
            call(client, "DEMO-001", "approve", {"change_id": result["change_id"]}).status_code
            == 403
        )
        result = call(
            client, "DEMO-001", "approve", {"change_id": result["change_id"]}, "admin"
        ).json()
    assert result["total"] == ("6005.00" if late else "5990.00")
    audit = client.get("/events/DEMO-001/audit", headers=auth()).json()
    applied = next(row for row in audit if row["name"] == "CambioAplicado")
    assert "PROV-001" in applied["payload"]["recipients"]
    assert applied["payload"]["change"]["previous"]["guests"] == 100
    assert result["proposal"]["versions"][0]["total"] == "5890.00"
    assert request["state"] == "PENDIENTE"


def test_client_change_waits_for_commercial_review(client):
    confirmed(client)
    result = call(
        client, "DEMO-001", "change", {"menu": "Vegetariano", "increment": "0"}, "client"
    ).json()
    assert result["changes"][0]["state"] == "PENDIENTE"
    result = call(client, "DEMO-001", "approve", {"change_id": result["change_id"]}, "admin")
    assert result.json()["menu"] == "Vegetariano"


def test_post_event_liquidation_follows_U3_H1(client):
    confirmed(client, day="2026-11-06")
    request = assign(client).json()
    client.post(
        f"/requests/{request['id']}/respond", json={"accepted": True}, headers=auth("supplier")
    )
    assert call(client, "DEMO-001", "start").status_code == 200
    assert call(client, "DEMO-001", "finish").status_code == 200
    assert call(client, "DEMO-001", "close", {"act": "A"}).status_code == 422
    result = call(
        client,
        "DEMO-001",
        "pay",
        {"amount": "4123.00", "reference": "POSTEVENTO", "method": "TERMINAL"},
        "admin",
    )
    assert result.json()["balance"] == "0.00"
    assert call(client, "DEMO-001", "close", {"act": "A"}).status_code == 200


def test_reject_proposal_and_pending_change(client):
    client.post("/events", json=payload(day="2026-11-20"), headers=auth())
    call(client, "DEMO-001", "send")
    assert (
        call(client, "DEMO-001", "reject", {"reason": "Ajustar menú"}, "client").json()["proposal"][
            "state"
        ]
        == "BORRADOR"
    )
    call(
        client,
        "DEMO-001",
        "revise",
        {"items": [{"resource_id": "EVE-P001", "quantity": 10}], "reason": "Revisión"},
    )
    call(client, "DEMO-001", "send")
    call(client, "DEMO-001", "accept", role="client")
    call(client, "DEMO-001", "sign", {"reference": "C"}, "client")
    call(
        client,
        "DEMO-001",
        "pay",
        {"amount": "1767", "reference": "P", "method": "TERMINAL"},
        "admin",
    )
    change = call(client, "DEMO-001", "change", {"schedule": "20:00", "increment": "100"}).json()
    rejected = call(
        client,
        "DEMO-001",
        "reject_change",
        {"change_id": change["change_id"], "reason": "Sin disponibilidad"},
        "admin",
    )
    assert rejected.json()["total"] == "5890.00"
    assert rejected.json()["changes"][0]["state"] == "RECHAZADO"
    assert (
        call(client, "DEMO-001", "approve", {"change_id": change["change_id"]}, "admin").status_code
        == 409
    )


def test_US06_48_hours_and_expiration_idempotence(client, clock):
    confirmed(client)
    request = assign(client).json()
    clock.value += timedelta(hours=48)
    assert (
        client.post(
            f"/requests/{request['id']}/respond", json={"accepted": True}, headers=auth("supplier")
        ).status_code
        == 422
    )
    response = client.post("/requests/expire", headers=auth())
    assert response.json()["expired"] == [request["id"]]
    assert client.post("/requests/expire", headers=auth()).json()["expired"] == []
    assert client.get("/requests", headers=auth("supplier")).json()[0]["state"] == "EXPIRADO"


def test_US11_backup_replacement_and_booking(client):
    confirmed(client)
    request = assign(client).json()
    assert (
        client.post(
            f"/requests/{request['id']}/respond", json={"accepted": True}, headers=auth("supplier")
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/requests/{request['id']}/cancel",
            json={"reason": "Falla técnica"},
            headers=auth("supplier"),
        ).status_code
        == 200
    )
    assert assign(client, replaces=request["id"]).status_code == 422
    replacement = assign(client, supplier="PROV-002", replaces=request["id"])
    assert replacement.status_code == 201
    assert assign(client, supplier="PROV-002", replaces=request["id"]).status_code == 409
    rid = replacement.json()["id"]
    assert (
        client.post(
            f"/requests/{rid}/respond", json={"accepted": True}, headers=auth("backup")
        ).status_code
        == 200
    )
    assert (
        client.get("/events/DEMO-001/profitability", headers=auth("admin")).json()["supplier_cost"]
        == "1000.00"
    )


def test_supplier_cannot_double_book_date(client):
    confirmed(client)
    confirmed(client, "DEMO-002")
    first, second = assign(client).json(), assign(client, "DEMO-002").json()
    assert (
        client.post(
            f"/requests/{first['id']}/respond", json={"accepted": True}, headers=auth("supplier")
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/requests/{second['id']}/respond", json={"accepted": True}, headers=auth("supplier")
        ).status_code
        == 409
    )
    assert (
        client.get("/events/DEMO-002/profitability", headers=auth("admin")).json()["supplier_cost"]
        == "0.00"
    )
    requests = client.get("/requests", params={"event_id": "DEMO-002"}, headers=auth()).json()
    assert requests[0]["state"] == "PENDIENTE"


def test_cancel_retains_nonrefundable_advance_and_releases_supplier(client):
    confirmed(client)
    request = assign(client).json()
    client.post(
        f"/requests/{request['id']}/respond", json={"accepted": True}, headers=auth("supplier")
    )
    result = call(client, "DEMO-001", "cancel", {"reason": "Cliente desiste"}, "admin")
    assert result.json()["paid"] == "1767.00"
    assert result.json()["state"] == "CANCELADO"
    assert client.get("/requests", headers=auth()).json()[0]["state"] == "CANCELADO"


@pytest.mark.parametrize(
    "action,body",
    [
        ("pay", {"amount": "100", "reference": "P", "method": "TERMINAL"}),
        ("close", {"act": "A"}),
        ("start", {}),
        ("finish", {}),
        ("send", {}),
        ("approve", {"change_id": "C"}),
    ],
)
def test_role_checks_prevent_escalation(client, action, body):
    confirmed(client)
    assert call(client, "DEMO-001", action, body, "client").status_code == 403


def test_authentication_ownership_and_hidden_finances(client):
    confirmed(client)
    assert client.get("/events").status_code == 401
    assert client.get("/events", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/events/DEMO-001", headers=auth("other")).status_code == 403
    assert client.get("/events/DEMO-001", headers=auth("supplier")).status_code == 403
    assert client.get("/events/DEMO-001/audit", headers=auth("client")).status_code == 403
    assert client.get("/events/DEMO-001/profitability", headers=auth()).status_code == 403
    assert client.get("/me", headers=auth("client")).json()["role"] == "CLIENTE"
    assert all(
        row["client_id"] == "EVE-C001"
        for row in client.get("/events", headers=auth("client")).json()
    )
    assert client.get("/events/no-existe", headers=auth()).status_code == 404
    assert call(client, "no-existe", "send").status_code == 404
    request = assign(client).json()
    assert (
        client.post(
            f"/requests/{request['id']}/respond", json={"accepted": True}, headers=auth("backup")
        ).status_code
        == 403
    )


@pytest.mark.parametrize(
    "patch",
    [
        {"guests": 0},
        {"guests": True},
        {"event_date": "bad"},
        {"event_date": "2026-11-05"},
        {"items": []},
        {"items": [{"resource_id": "EVE-P001", "quantity": 0}]},
        {"items": [{"resource_id": "EVE-P001", "quantity": 14}]},
        {"items": [{"resource_id": "EVE-P001", "quantity": 1}] * 2},
        {"role": "ADMIN"},
    ],
)
def test_bad_input_is_422_and_rolls_back(client, patch):
    response = client.post("/events", json={**payload(), **patch}, headers=auth())
    assert response.status_code == 422, response.text
    assert client.get("/events/DEMO-001", headers=auth()).status_code == 404


def test_resource_and_supplier_errors(client):
    assert (
        client.post(
            "/events",
            json={**payload(), "items": [{"resource_id": "missing", "quantity": 1}]},
            headers=auth(),
        ).status_code
        == 404
    )
    assert client.get("/catalogs/unknown", headers=auth()).status_code == 422
    assert len(client.get("/catalogs/resource", headers=auth()).json()) == 20
    assert len(client.get("/catalogs/client", headers=auth()).json()) == 40
    assert len(client.get("/catalogs/supplier", headers=auth()).json()) == 3
    assert client.get("/catalogs/client", headers=auth("client")).status_code == 403
    assert client.post("/events", json=payload(), headers=auth()).status_code == 201
    assert assign(client).status_code == 409
    assert client.post("/events", json=payload(), headers=auth()).status_code == 409
    call(client, "DEMO-001", "send")
    call(client, "DEMO-001", "accept", role="client")
    call(client, "DEMO-001", "sign", {"reference": "C"}, "client")
    call(
        client,
        "DEMO-001",
        "pay",
        {"amount": "1767", "reference": "P", "method": "TERMINAL"},
        "admin",
    )
    assert assign(client, supplier="PROV-003").status_code == 422
    assert assign(client, supplier="PROV-002", replaces="missing").status_code == 404


def test_OpenAPI_and_health(client):
    assert client.get("/health").json()["status"] == "ok"
    schema = client.get("/openapi.json").json()
    assert schema["components"]["securitySchemes"]["HTTPBearer"]["scheme"] == "bearer"
    assert "/events/{event_id}/change" in schema["paths"]
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200


def test_midnight_uses_mexico_calendar_date(client, clock):
    # UTC 7/nov 02:00 todavía es 6/nov en Monterrey.
    clock.value = datetime(2026, 11, 7, 2, tzinfo=timezone.utc)
    assert client.post("/events", json=payload(day="2026-11-06"), headers=auth()).status_code == 201
