from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta

from src.domain.errors import BusinessError, Conflict
from src.domain.value_objects import amount, required


@dataclass
class SupplierRequest:
    id: str
    event_id: str
    supplier_id: str
    service: str
    cost: str
    sent_at: str
    state: str = "PENDIENTE"
    answered_at: str | None = None
    replaces: str | None = None

    def __post_init__(self):
        required(self.service, "Servicio")
        self.cost = str(amount(self.cost))

    @property
    def deadline(self):
        return datetime.fromisoformat(self.sent_at) + timedelta(hours=48)

    def respond(self, accepted: bool, now: datetime):
        if self.state != "PENDIENTE":
            raise Conflict("La solicitud ya tiene resolución")
        if now >= self.deadline:
            raise BusinessError("Plazo de 48 horas vencido")
        self.state = "CONFIRMADO" if accepted else "RECHAZADO"
        self.answered_at = now.isoformat()

    def expire(self, now: datetime):
        if self.state == "PENDIENTE" and now >= self.deadline:
            self.state = "EXPIRADO"
            self.answered_at = now.isoformat()
            return True
        return False

    def cancel(self, reason: str, now: datetime):
        required(reason, "Motivo")
        if self.state != "CONFIRMADO":
            raise Conflict("Solo cancela una asignación confirmada")
        self.state = "CANCELADO"
        self.answered_at = now.isoformat()

    def to_dict(self):
        return deepcopy(vars(self))

    @classmethod
    def from_dict(cls, data):
        return cls(**deepcopy(data))
