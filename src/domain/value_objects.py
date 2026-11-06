from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from src.domain.errors import BusinessError


def amount(value) -> Decimal:
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0:
            raise BusinessError("Importe finito no negativo requerido")
        return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise BusinessError("Importe inválido") from exc


def required(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BusinessError(f"{label} requerido")
    return value.strip()


@dataclass(frozen=True)
class Money:
    value: Decimal
    currency: str = "MXN"

    def __post_init__(self):
        object.__setattr__(self, "value", amount(self.value))
        if self.currency != "MXN":
            raise BusinessError("Solo se admiten importes en MXN")


@dataclass(frozen=True)
class Line:
    resource_id: str
    description: str
    quantity: int
    price: Money

    def __post_init__(self):
        required(self.resource_id, "Recurso")
        required(self.description, "Descripción")
        if (
            isinstance(self.quantity, bool)
            or not isinstance(self.quantity, int)
            or self.quantity <= 0
        ):
            raise BusinessError("Cantidad entera positiva requerida")

    @property
    def subtotal(self):
        return amount(self.quantity * self.price.value)

    def to_dict(self):
        return {
            "resource_id": self.resource_id,
            "description": self.description,
            "quantity": self.quantity,
            "price": str(self.price.value),
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data["resource_id"], data["description"], data["quantity"], Money(data["price"]))
