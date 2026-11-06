from datetime import date
from uuid import uuid4
from zoneinfo import ZoneInfo

from src.application.ports import SystemClock
from src.domain.errors import BusinessError, Conflict, Forbidden
from src.domain.event import Event
from src.domain.policies import ChangePolicy
from src.domain.proposal import Proposal
from src.domain.supplier import SupplierRequest
from src.domain.value_objects import Line, Money, amount, required


class NovaService:
    def __init__(self, uow_factory, clock=None, timezone="America/Mexico_City"):
        self.uow_factory = uow_factory
        self.clock = clock or SystemClock()
        self.timezone = ZoneInfo(timezone)

    def now(self):
        return self.clock.now()

    def today(self):
        return self.now().astimezone(self.timezone).date()

    def emit(self, uow, name, event_id, principal, payload=None):
        uow.emit(name, event_id, principal.id, self.now().isoformat(), payload or {})

    def lines(self, uow, items):
        lines = []
        seen = set()
        for item in items:
            resource = uow.get("resource", item["resource_id"])
            quantity = item["quantity"]
            if item["resource_id"] in seen:
                raise BusinessError("Recurso duplicado en la propuesta")
            seen.add(item["resource_id"])
            if not resource["enabled"] or quantity > resource["capacity"]:
                raise BusinessError("Recurso deshabilitado o capacidad insuficiente")
            lines.append(
                Line(resource["id"], resource["description"], quantity, Money(resource["price"]))
            )
        return lines

    def create_event(self, principal, data):
        principal.require("COORDINADOR", "ADMIN")
        if date.fromisoformat(data["event_date"]) < self.today():
            raise BusinessError("La fecha no puede estar en el pasado")
        with self.uow_factory() as uow:
            client = uow.get("client", data["client_id"])
            if not client["active"]:
                raise BusinessError("Cliente inactivo")
            event_id = data.get("id") or str(uuid4())
            lines = self.lines(uow, data["items"])
            proposal = Proposal(event_id, event_id)
            version = proposal.revise(lines, self.now().isoformat(), principal.id, "Alta inicial")
            event = Event(
                event_id,
                data["client_id"],
                data["event_date"],
                data["title"],
                data["guests"],
                version["total"],
            )
            uow.save("event", event.id, event.to_dict())
            uow.save("proposal", proposal.id, proposal.to_dict())
            self.emit(uow, "PropuestaCreada", event.id, principal, {"version": "1.0"})
            uow.commit()
            return self.view(event, proposal)

    @staticmethod
    def view(event, proposal):
        result = event.to_dict()
        result.update(paid=str(event.paid), balance=str(event.balance), proposal=proposal.to_dict())
        return result

    def get_event(self, principal, event_id):
        with self.uow_factory() as uow:
            event = Event.from_dict(uow.get("event", event_id))
            principal.event_access(event)
            return self.view(event, Proposal.from_dict(uow.get("proposal", event_id)))

    def list_events(self, principal):
        principal.require("ADMIN", "COORDINADOR", "CLIENTE")
        with self.uow_factory() as uow:
            return [
                e
                for e in uow.list("event")
                if principal.role != "CLIENTE" or e["client_id"] == principal.id
            ]

    def catalog(self, principal, kind):
        principal.require("ADMIN", "COORDINADOR", "CLIENTE", "PROVEEDOR")
        if kind not in {"client", "resource", "supplier"}:
            raise BusinessError("Catálogo desconocido")
        if kind == "client":
            principal.require("ADMIN", "COORDINADOR")
        with self.uow_factory() as uow:
            return uow.list(kind)

    def execute(self, principal, event_id, command, data=None):
        data = data or {}
        role_map = {
            "send": ("COORDINADOR", "ADMIN"),
            "accept": ("CLIENTE",),
            "sign": ("CLIENTE",),
            "reject": ("CLIENTE",),
            "pay": ("ADMIN",),
            "revise": ("COORDINADOR",),
            "change": ("CLIENTE", "COORDINADOR"),
            "approve": ("ADMIN",),
            "reject_change": ("ADMIN",),
            "extra": ("COORDINADOR",),
            "pay_extra": ("ADMIN",),
            "deliver_extra": ("COORDINADOR",),
            "start": ("COORDINADOR",),
            "finish": ("COORDINADOR",),
            "close": ("COORDINADOR",),
            "cancel": ("ADMIN",),
        }
        if command not in role_map:
            raise BusinessError("Comando desconocido")
        principal.require(*role_map[command])
        with self.uow_factory() as uow:
            event = Event.from_dict(uow.get("event", event_id))
            principal.event_access(event)
            proposal = Proposal.from_dict(uow.get("proposal", event_id))
            previous = event.state
            now = self.now().isoformat()
            result = {}
            if command == "send":
                proposal.send(uow.get("client", event.client_id)["active"], True)
            elif command == "accept":
                proposal.accept()
                event.accept()
            elif command == "reject":
                required(data["reason"], "Motivo")
                proposal.reject()
            elif command == "sign":
                event.sign(data["reference"], now, principal.id)
            elif command == "pay":
                event.pay(data["amount"], data["reference"], data["method"], now)
            elif command == "revise":
                if event.state != "BORRADOR":
                    raise Conflict("Las revisiones directas requieren evento en borrador")
                snapshot = proposal.revise(
                    self.lines(uow, data["items"]),
                    now,
                    principal.id,
                    required(data["reason"], "Motivo"),
                )
                event.total = snapshot["total"]
            elif command == "change":
                evaluation = ChangePolicy().evaluate(
                    date.fromisoformat(event.event_date), self.today(), data["increment"]
                )
                change = event.request_change(str(uuid4()), data, evaluation, now, principal.id)
                if not evaluation["late"] and principal.role == "COORDINADOR":
                    self.apply_change(event, proposal, change["id"], principal, uow)
                result = {"change_id": change["id"], "evaluation": evaluation}
            elif command == "approve":
                self.apply_change(event, proposal, data["change_id"], principal, uow)
            elif command == "reject_change":
                event.reject_change(data["change_id"], data["reason"], now, principal.id)
            elif command == "extra":
                extra_id = str(uuid4())
                event.add_extra(extra_id, data["description"], data["amount"], now)
                self.append_version(proposal, event, principal, "Adicional", data["amount"])
                result = {"extra_id": extra_id}
            elif command == "pay_extra":
                event.pay_extra(data["extra_id"], data["reference"], data["method"], now)
            elif command == "deliver_extra":
                event.deliver_extra(data["extra_id"], now)
            elif command == "start":
                requests = [s for s in uow.list("request") if s["event_id"] == event_id]
                replaced = {s["replaces"] for s in requests if s["replaces"]}
                latest = [s for s in requests if s["id"] not in replaced]
                event.start(
                    self.today(), bool(latest) and all(s["state"] == "CONFIRMADO" for s in latest)
                )
            elif command == "finish":
                event.finish()
            elif command == "close":
                event.close(data["act"], now, principal.id)
            elif command == "cancel":
                event.cancel(data["reason"])
                for request in uow.list("request"):
                    if request["event_id"] == event_id and request["state"] in {
                        "PENDIENTE",
                        "CONFIRMADO",
                    }:
                        request["state"] = "CANCELADO"
                        uow.save("request", request["id"], request)
                        uow.release(request["id"])
            uow.save("event", event.id, event.to_dict())
            uow.save("proposal", proposal.id, proposal.to_dict())
            self.emit(
                uow,
                {
                    "send": "PropuestaEnviada",
                    "accept": "PropuestaAceptada",
                    "sign": "ContratoFirmado",
                    "reject": "PropuestaRechazada",
                    "pay": "PagoRegistrado",
                    "revise": "PropuestaVersionada",
                    "change": "CambioSolicitado",
                    "approve": "CambioAutorizado",
                    "reject_change": "CambioRechazado",
                    "extra": "AdicionalRegistrado",
                    "pay_extra": "AdicionalPagado",
                    "deliver_extra": "AdicionalPrestado",
                    "start": "EventoIniciado",
                    "finish": "EventoFinalizado",
                    "close": "EventoCerrado",
                    "cancel": "EventoCancelado",
                }[command],
                event.id,
                principal,
                {"previous": previous, "new": event.state, "result": result},
            )
            uow.commit()
            return {**self.view(event, proposal), **result}

    def append_version(self, proposal, event, principal, reason, increment):
        lines = [Line.from_dict(line) for line in proposal.current["lines"]]
        if amount(increment):
            lines.append(Line("AJUSTE-" + str(len(proposal.versions)), reason, 1, Money(increment)))
        snapshot = proposal.revise(lines, self.now().isoformat(), principal.id, reason)
        if amount(snapshot["total"]) != amount(event.total):
            raise BusinessError("La propuesta y el evento deben conservar el mismo total")

    def apply_change(self, event, proposal, change_id, principal, uow):
        change = event.apply_change(change_id, self.now().isoformat(), principal.id)
        increment = amount(change["data"]["increment"]) + amount(change["evaluation"]["charge"])
        self.append_version(proposal, event, principal, "Cambio " + change_id, increment)
        recipients = sorted(
            {
                r["supplier_id"]
                for r in uow.list("request")
                if r["event_id"] == event.id and r["state"] in {"CONFIRMADO", "PENDIENTE"}
            }
        )
        self.emit(
            uow,
            "CambioAplicado",
            event.id,
            principal,
            {
                "change": change,
                "version": proposal.current["number"],
                "recipients": recipients + [event.client_id, "COORDINACION"],
            },
        )

    def request_supplier(self, principal, event_id, data):
        principal.require("COORDINADOR")
        with self.uow_factory() as uow:
            event = Event.from_dict(uow.get("event", event_id))
            if event.state != "CONFIRMADO":
                raise Conflict("La asignación requiere evento confirmado")
            supplier = uow.get("supplier", data["supplier_id"])
            if not supplier["active"]:
                raise BusinessError("Proveedor inactivo")
            if data.get("replaces"):
                old = uow.get("request", data["replaces"])
                if old["event_id"] != event_id or old["state"] not in {
                    "CANCELADO",
                    "RECHAZADO",
                    "EXPIRADO",
                }:
                    raise BusinessError("Sustitución inválida")
                if any(r["replaces"] == old["id"] for r in uow.list("request")):
                    raise Conflict("La solicitud ya tiene sustitución")
                if not supplier["backup"]:
                    raise BusinessError("La contingencia requiere proveedor Backup")
            request = SupplierRequest(
                str(uuid4()),
                event_id,
                supplier["id"],
                data["service"],
                data["cost"],
                self.now().isoformat(),
                replaces=data.get("replaces"),
            )
            uow.save("request", request.id, request.to_dict())
            self.emit(
                uow,
                "SolicitudAProveedorEnviada",
                event_id,
                principal,
                {
                    "request_id": request.id,
                    "recipient": supplier["id"],
                    "replaces": request.replaces,
                    "deadline": request.deadline.isoformat(),
                },
            )
            uow.commit()
            return request.to_dict()

    def supplier_action(self, principal, request_id, command, data):
        principal.require("PROVEEDOR")
        with self.uow_factory() as uow:
            request = SupplierRequest.from_dict(uow.get("request", request_id))
            if request.supplier_id != principal.id:
                raise Forbidden("La solicitud pertenece a otro proveedor")
            event = Event.from_dict(uow.get("event", request.event_id))
            if event.state != "CONFIRMADO":
                raise Conflict("El evento ya no admite respuestas de proveedores")
            if command == "respond":
                request.respond(data["accepted"], self.now())
                if data["accepted"]:
                    uow.book(request.supplier_id, event.event_date, request.id)
                    event.supplier_cost = str(
                        amount(amount(event.supplier_cost) + amount(request.cost))
                    )
            elif command == "cancel":
                request.cancel(data["reason"], self.now())
                uow.release(request.id)
                event.supplier_cost = str(
                    amount(amount(event.supplier_cost) - amount(request.cost))
                )
            else:
                raise BusinessError("Acción de proveedor inválida")
            uow.save("request", request.id, request.to_dict())
            uow.save("event", event.id, event.to_dict())
            backups = (
                [s for s in uow.list("supplier") if s["active"] and s["backup"]]
                if command == "cancel"
                else []
            )
            self.emit(
                uow,
                "Proveedor" + request.state.title(),
                event.id,
                principal,
                {"request_id": request.id, "state": request.state, "recipient": "COORDINACION"},
            )
            uow.commit()
            return {**request.to_dict(), "backups": backups}

    def expire_requests(self, principal):
        principal.require("ADMIN", "COORDINADOR")
        with self.uow_factory() as uow:
            expired = []
            for data in uow.list("request"):
                request = SupplierRequest.from_dict(data)
                if request.expire(self.now()):
                    uow.save("request", request.id, request.to_dict())
                    self.emit(
                        uow,
                        "SolicitudDeProveedorExpirada",
                        request.event_id,
                        principal,
                        {"request_id": request.id, "recipient": "COORDINACION"},
                    )
                    expired.append(request.id)
            uow.commit()
            return {"expired": expired}

    def requests(self, principal, event_id=None):
        principal.require("ADMIN", "COORDINADOR", "PROVEEDOR")
        with self.uow_factory() as uow:
            return [
                r
                for r in uow.list("request")
                if (not event_id or r["event_id"] == event_id)
                and (principal.role != "PROVEEDOR" or r["supplier_id"] == principal.id)
            ]

    def audit(self, principal, event_id):
        principal.require("ADMIN", "COORDINADOR")
        with self.uow_factory() as uow:
            uow.get("event", event_id)
            return uow.events(event_id)

    def profitability(self, principal, event_id):
        principal.require("ADMIN")
        with self.uow_factory() as uow:
            event = Event.from_dict(uow.get("event", event_id))
            return {
                "event_id": event.id,
                "income": event.total,
                "collected": str(event.paid),
                "supplier_cost": event.supplier_cost,
                "margin": str(amount(event.total) - amount(event.supplier_cost)),
                "currency": "MXN",
            }
