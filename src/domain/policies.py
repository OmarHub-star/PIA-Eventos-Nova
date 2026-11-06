from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.domain.errors import BusinessError
from src.domain.value_objects import amount


@dataclass(frozen=True)
class ChangePolicy:
    free_days: int = 15
    rate: Decimal = Decimal("0.15")

    def evaluate(self, event_date: date, requested_date: date, increment):
        days = (event_date - requested_date).days
        if days < 0:
            raise BusinessError("No se admiten cambios posteriores al evento")
        late = days < self.free_days
        return {
            "late": late,
            "charge": str(amount(amount(increment) * self.rate) if late else amount(0)),
            "days": days,
        }
