from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from src.domain.errors import BusinessError, Conflict
from src.domain.specifications import CAN_CLOSE
from src.domain.state_machine import next_state
from src.domain.value_objects import amount, required


@dataclass
class Event:
    id: str
    client_id: str
    event_date: str
    title: str
    guests: int
    total: str
    state: str = "BORRADOR"
    contract: dict | None = None
    payments: list[dict] = field(default_factory=list)
    changes: list[dict] = field(default_factory=list)
    extras: list[dict] = field(default_factory=list)
    menu: str = "Por definir"
    schedule: str = "Por definir"
    closure: dict | None = None
    supplier_cost: str = "0.00"

    def __post_init__(self):
        required(self.id, "Evento")
        required(self.client_id, "Cliente")
        required(self.title, "Título")
        date.fromisoformat(self.event_date)
        if isinstance(self.guests, bool) or not isinstance(self.guests, int) or self.guests <= 0:
            raise BusinessError("Aforo entero positivo requerido")
        self.total = str(amount(self.total))

    @property
    def paid(self):
        return amount(sum((amount(p["amount"]) for p in self.payments), Decimal(0)))

    @property
    def balance(self):
        return amount(amount(self.total) - self.paid)

    def accept(self):
        self.state = next_state(self.state, "ACEPTADO")

    def sign(self, reference: str, when: str, responsible: str):
        if self.state != "ACEPTADO" or self.contract:
            raise Conflict("El contrato se firma una vez tras aceptar la propuesta")
        self.contract = {
            "reference": required(reference, "Contrato"),
            "signed_at": when,
            "responsible": responsible,
            "signed_total": self.total,
        }

    def pay(self, value, reference: str, method: str, when: str):
        value = amount(value)
        reference = required(reference, "Referencia de pago")
        if self.state not in {"ACEPTADO", "CONFIRMADO", "FINALIZADO", "EN_EJECUCION"}:
            raise Conflict("El estado no admite pagos")
        if not self.contract:
            raise BusinessError("Se requiere contrato firmado")
        if value <= 0 or value > self.balance:
            raise BusinessError("Pago positivo y no mayor al saldo requerido")
        if method not in {"TRANSFERENCIA", "TERMINAL", "EFECTIVO"}:
            raise BusinessError("Método de pago inválido")
        if any(p["reference"] == reference for p in self.payments):
            raise Conflict("Referencia de pago duplicada")
        self.payments.append(
            {"amount": str(value), "reference": reference, "method": method, "paid_at": when}
        )
        if self.state == "ACEPTADO" and self.paid >= amount(
            amount(self.contract["signed_total"]) * Decimal("0.30")
        ):
            self.state = next_state(self.state, "CONFIRMADO")

    def request_change(
        self, change_id: str, data: dict, evaluation: dict, when: str, responsible: str
    ):
        if self.state != "CONFIRMADO":
            raise Conflict("Solo se modifica un evento confirmado")
        if any(c["state"] == "PENDIENTE" for c in self.changes):
            raise Conflict("Resuelva el cambio pendiente antes de solicitar otro")
        if not any(k in data for k in ("guests", "menu", "schedule")):
            raise BusinessError("Debe modificar aforo, menú u horario")
        if "guests" in data and (
            isinstance(data["guests"], bool)
            or not isinstance(data["guests"], int)
            or data["guests"] <= 0
        ):
            raise BusinessError("Aforo entero positivo requerido")
        for k in ("menu", "schedule"):
            if k in data:
                required(data[k], k)
        change = {
            "id": change_id,
            "data": deepcopy(data),
            "evaluation": evaluation,
            "requested_at": when,
            "requested_by": responsible,
            "previous": {k: getattr(self, k) for k in ("guests", "menu", "schedule")},
            "state": "PENDIENTE",
        }
        self.changes.append(change)
        return change

    def apply_change(self, change_id: str, when: str, responsible: str):
        change = next((c for c in self.changes if c["id"] == change_id), None)
        if not change:
            raise BusinessError("Cambio inexistente")
        if self.state != "CONFIRMADO" or change["state"] != "PENDIENTE":
            raise Conflict("El cambio no puede aplicarse")
        for k in ("guests", "menu", "schedule"):
            if k in change["data"]:
                setattr(self, k, change["data"][k])
        self.total = str(
            amount(
                amount(self.total)
                + amount(change["data"]["increment"])
                + amount(change["evaluation"]["charge"])
            )
        )
        change.update(state="APLICADO", approved_at=when, approved_by=responsible)
        return change

    def reject_change(self, change_id: str, reason: str, when: str, responsible: str):
        change = next((c for c in self.changes if c["id"] == change_id), None)
        if not change:
            raise BusinessError("Cambio inexistente")
        if self.state != "CONFIRMADO" or change["state"] != "PENDIENTE":
            raise Conflict("El cambio no está pendiente")
        change.update(
            state="RECHAZADO",
            reason=required(reason, "Motivo"),
            rejected_at=when,
            rejected_by=responsible,
        )

    def add_extra(self, extra_id: str, description: str, value, when: str):
        if self.state not in {"CONFIRMADO", "EN_EJECUCION"}:
            raise Conflict("Estado inválido para agregar servicios")
        value = amount(value)
        if value <= 0:
            raise BusinessError("El servicio debe tener importe positivo")
        self.extras.append(
            {
                "id": extra_id,
                "description": required(description, "Servicio"),
                "amount": str(value),
                "registered_at": when,
                "payment_reference": None,
                "delivered_at": None,
            }
        )
        self.total = str(amount(amount(self.total) + value))

    def pay_extra(self, extra_id: str, reference: str, method: str, when: str):
        extra = self.get_extra(extra_id)
        if extra["payment_reference"]:
            raise Conflict("El adicional ya tiene pago")
        if method not in {"TRANSFERENCIA", "TERMINAL"}:
            raise BusinessError("BR08 requiere transferencia o terminal")
        self.pay(extra["amount"], reference, method, when)
        extra["payment_reference"] = reference

    def get_extra(self, extra_id: str):
        extra = next((x for x in self.extras if x["id"] == extra_id), None)
        if not extra:
            raise BusinessError("Servicio adicional inexistente")
        return extra

    def deliver_extra(self, extra_id: str, when: str):
        extra = self.get_extra(extra_id)
        if self.state != "EN_EJECUCION" or not extra["payment_reference"]:
            raise BusinessError("Se requiere ejecución y pago previo del adicional")
        if extra["delivered_at"]:
            raise Conflict("El servicio ya fue prestado")
        extra["delivered_at"] = when

    def start(self, today: date, suppliers_ready: bool):
        if today != date.fromisoformat(self.event_date):
            raise BusinessError("La ejecución requiere la fecha del evento")
        if not suppliers_ready or any(c["state"] == "PENDIENTE" for c in self.changes):
            raise BusinessError("Requiere proveedores confirmados y cambios resueltos")
        self.state = next_state(self.state, "EN_EJECUCION")

    def finish(self):
        if any(not e["delivered_at"] for e in self.extras):
            raise BusinessError("Resuelva los servicios adicionales antes de finalizar")
        self.state = next_state(self.state, "FINALIZADO")

    def close(self, act: str, when: str, responsible: str):
        complete = bool(
            self.contract
            and not any(c["state"] == "PENDIENTE" for c in self.changes)
            and all(e["delivered_at"] for e in self.extras)
        )
        if not CAN_CLOSE.is_satisfied_by({"balance": self.balance, "complete": complete}):
            raise BusinessError("No puede cerrar con saldo o información pendiente")
        act = required(act, "Acta de cierre")
        self.state = next_state(self.state, "CERRADO")
        self.closure = {"act": act, "at": when, "responsible": responsible}

    def cancel(self, reason: str):
        required(reason, "Motivo de cancelación")
        self.state = next_state(self.state, "CANCELADO")

    def to_dict(self):
        return deepcopy(vars(self))

    @classmethod
    def from_dict(cls, data):
        return cls(**deepcopy(data))
