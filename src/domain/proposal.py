from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal

from src.domain.errors import BusinessError, Conflict
from src.domain.specifications import CAN_SEND
from src.domain.value_objects import Line, amount


@dataclass
class Proposal:
    id: str
    event_id: str
    versions: list[dict] = field(default_factory=list)
    state: str = "BORRADOR"

    def revise(self, lines: list[Line], when: str, responsible: str, reason: str):
        if self.state == "ENVIADA":
            raise Conflict("Resuelva la propuesta enviada antes de modificarla")
        snapshot = {
            "number": f"1.{len(self.versions)}",
            "created_at": when,
            "responsible": responsible,
            "reason": reason,
            "lines": [line.to_dict() for line in lines],
            "total": str(amount(sum((line.subtotal for line in lines), Decimal(0)))),
        }
        self.versions.append(snapshot)
        return deepcopy(snapshot)

    @property
    def current(self):
        if not self.versions:
            raise BusinessError("La propuesta requiere una versión")
        return deepcopy(self.versions[-1])

    def send(self, active: bool, authorized: bool):
        if self.state != "BORRADOR":
            raise Conflict("Solo se envía una propuesta en borrador")
        if not CAN_SEND.is_satisfied_by(
            {"active": active, "lines": self.current["lines"], "authorized": authorized}
        ):
            raise BusinessError("Requiere cliente activo, detalle y autorización")
        self.state = "ENVIADA"

    def accept(self):
        if self.state != "ENVIADA":
            raise Conflict("Solo se acepta una propuesta enviada")
        self.state = "ACEPTADA"

    def reject(self):
        if self.state != "ENVIADA":
            raise Conflict("Solo se rechaza una propuesta enviada")
        self.state = "BORRADOR"

    def to_dict(self):
        return deepcopy(vars(self))

    @classmethod
    def from_dict(cls, data):
        return cls(**deepcopy(data))
