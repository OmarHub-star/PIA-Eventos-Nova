"""Adaptación explícita de datos didácticos. No importa reglas VIP al dominio."""

import csv
from datetime import date, timedelta
from pathlib import Path

from src.domain.event import Event
from src.domain.proposal import Proposal
from src.domain.value_objects import Line, Money

DATA = Path(__file__).resolve().parents[2] / "data" / "original"


def rows(filename, folder=DATA):
    with (Path(folder) / filename).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def seed(uow_factory, folder=DATA):
    with uow_factory() as uow:
        if uow.list("client"):
            return {"status": "already_loaded"}
        clients = rows("actores.csv", folder)
        resources = rows("catalogo.csv", folder)
        for client in clients:
            uow.save(
                "client",
                client["actor_id"],
                {
                    "id": client["actor_id"],
                    "name": client["nombre"],
                    "active": client["activo"] == "1",
                    "city": client["ciudad"],
                },
            )
        catalog = {}
        for resource in resources:
            value = {
                "id": resource["recurso_id"],
                "description": resource["descripcion"],
                "price": resource["precio_mxn"],
                "capacity": int(resource["capacidad_o_stock"]),
                "enabled": resource["habilitado"] == "1",
            }
            catalog[value["id"]] = value
            uow.save("resource", value["id"], value)
        details = rows("detalle_operaciones.csv", folder)
        operations = rows("operaciones.csv", folder)
        for operation in operations:
            event_id = operation["operacion_id"]
            lines = [
                Line(
                    d["recurso_id"],
                    catalog[d["recurso_id"]]["description"],
                    int(d["cantidad"]),
                    Money(catalog[d["recurso_id"]]["price"]),
                )
                for d in details
                if d["operacion_id"] == event_id
            ]
            proposal = Proposal(event_id, event_id)
            version = proposal.revise(
                lines, operation["fecha_solicitud"], "IMPORTADOR", "CSV original"
            )
            # La fecha del evento no existe en el CSV. Se deriva +60 días y se documenta.
            day = date.fromisoformat(operation["fecha_solicitud"]) + timedelta(days=60)
            event = Event(
                event_id,
                operation["actor_id"],
                day.isoformat(),
                operation["referencia"],
                max(1, sum(line.quantity for line in lines)),
                version["total"],
            )
            uow.save("event", event_id, event.to_dict())
            uow.save("proposal", event_id, proposal.to_dict())
        # Proveedores complementarios de demostración; los CSV no incluyen esta entidad.
        for supplier in [
            {"id": "PROV-001", "name": "Banquetes Demo", "active": True, "backup": False},
            {"id": "PROV-002", "name": "Backup Demo", "active": True, "backup": True},
            {"id": "PROV-003", "name": "Proveedor inactivo Demo", "active": False, "backup": True},
        ]:
            uow.save("supplier", supplier["id"], supplier)
        uow.commit()
        return {"clients": len(clients), "resources": len(resources), "operations": len(operations)}
