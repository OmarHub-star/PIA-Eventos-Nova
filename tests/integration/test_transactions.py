import pytest
from sqlalchemy import select

from src.api.main import create_app
from src.application.security import Principal
from src.application.services import NovaService
from src.domain.errors import BusinessError, Conflict
from src.domain.event import Event
from src.infrastructure.database import SqlUnitOfWork, make_engine, metadata, outbox
from src.infrastructure.fixtures import seed
from tests.conftest import payload


def test_commit_and_reopen_real_database(tmp_path):
    url = "sqlite:///" + str(tmp_path / "persistent.db")
    engine = make_engine(url)
    metadata.create_all(engine)

    def factory():
        return SqlUnitOfWork(engine)

    seed(factory)
    with factory() as uow:
        client = uow.get("client", "EVE-C001")
        client["name"] = "Persistencia verificada"
        uow.save("client", client["id"], client)
        uow.emit("PruebaCommit", "E1", "test", "now", {})
        uow.commit()
    engine.dispose()
    reopened = make_engine(url)
    with SqlUnitOfWork(reopened) as uow:
        assert uow.get("client", "EVE-C001")["name"] == "Persistencia verificada"
        assert uow.events("E1")[0]["name"] == "PruebaCommit"
    reopened.dispose()


def test_rollback_aggregate_and_domain_event(database):
    with pytest.raises(RuntimeError):
        with database() as uow:
            client = uow.get("client", "EVE-C001")
            client["name"] = "NO PERSISTIR"
            uow.save("client", client["id"], client)
            uow.emit("NO_PUBLICAR", "E1", "test", "now", {})
            raise RuntimeError("Fallo antes del commit")
    with database() as uow:
        assert uow.get("client", "EVE-C001")["name"] != "NO PERSISTIR"
        assert uow.events("E1") == []


def test_optimistic_lock_rejects_stale_version(database):
    # Conserva una versión leída, ejecuta otra escritura y prueba la condición CAS.
    with database() as old:
        data = old.get("client", "EVE-C001")
        stale_version = old.versions[("client", "EVE-C001")]
    with database() as other:
        current = other.get("client", "EVE-C001")
        current["name"] = "Nueva versión"
        other.save("client", "EVE-C001", current)
        other.commit()
    with database() as stale:
        stale.versions[("client", "EVE-C001")] = stale_version
        with pytest.raises(Conflict):
            stale.save("client", "EVE-C001", data)
    with database() as uow:
        assert uow.get("client", "EVE-C001")["name"] == "Nueva versión"


def test_seed_idempotent_counts_and_fk_mapping(database):
    assert seed(database)["status"] == "already_loaded"
    with database() as uow:
        assert len(uow.list("client")) == 40
        assert len(uow.list("resource")) == 20
        assert len(uow.list("event")) == 60
        assert len(uow.list("proposal")) == 60
        ids = {c["id"] for c in uow.list("client")}
        assert all(e["client_id"] in ids for e in uow.list("event"))


def test_failed_change_rolls_back_event_proposal_and_notifications(
    database, clock, coordinator, monkeypatch
):
    service = NovaService(database, clock)
    service.create_event(coordinator, payload())
    client = Principal("EVE-C001", "CLIENTE")
    admin = Principal("ADM", "ADMIN")
    service.execute(coordinator, "DEMO-001", "send")
    service.execute(client, "DEMO-001", "accept")
    service.execute(client, "DEMO-001", "sign", {"reference": "C"})
    service.execute(
        admin, "DEMO-001", "pay", {"amount": "1767", "reference": "P", "method": "TERMINAL"}
    )
    before = service.get_event(coordinator, "DEMO-001")

    def fail(*args):
        raise RuntimeError("Fallo simulando el mapeo de propuesta")

    monkeypatch.setattr(service, "append_version", fail)
    with pytest.raises(RuntimeError):
        service.execute(coordinator, "DEMO-001", "change", {"guests": 120, "increment": "100"})
    assert service.get_event(coordinator, "DEMO-001") == before
    assert not any(e["name"] == "CambioAplicado" for e in service.audit(coordinator, "DEMO-001"))


def test_configuration_rejects_invalid_role():
    with pytest.raises(ValueError):
        create_app("sqlite:///:memory:", tokens={"token": {"id": "A", "role": "ROOT"}})


def test_in_memory_sqlite_factory():
    engine = make_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    with SqlUnitOfWork(engine) as uow:
        assert uow.connection.execute(select(outbox)).all() == []
    engine.dispose()


def test_internal_guard_for_unknown_commands(database, clock, coordinator):
    service = NovaService(database, clock)
    with pytest.raises(BusinessError):
        service.execute(coordinator, "missing", "unknown")
    item = Event("E1", "C1", "2026-12-06", "Evento", 1, "100")
    assert item.to_dict()["state"] == "BORRADOR"
