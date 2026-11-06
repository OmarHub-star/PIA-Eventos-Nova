from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

Text = Annotated[str, Field(min_length=1, max_length=500)]
Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")]
Amount = Annotated[Decimal, Field(ge=0, max_digits=14, decimal_places=2, allow_inf_nan=False)]


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Item(Body):
    resource_id: Identifier
    quantity: Annotated[int, Field(strict=True, gt=0, le=100000)]


class CreateEvent(Body):
    id: Identifier | None = None
    client_id: Identifier
    event_date: date
    title: Text
    guests: Annotated[int, Field(strict=True, gt=0, le=100000)]
    items: Annotated[list[Item], Field(min_length=1, max_length=100)]


class Empty(Body):
    pass


class Reference(Body):
    reference: Text


class Payment(Reference):
    amount: Amount
    method: Annotated[str, Field(pattern="^(TRANSFERENCIA|TERMINAL|EFECTIVO)$")]


class Revision(Body):
    items: Annotated[list[Item], Field(min_length=1, max_length=100)]
    reason: Text


class Change(Body):
    increment: Amount
    guests: Annotated[int, Field(strict=True, gt=0, le=100000)] | None = None
    menu: Text | None = None
    schedule: Text | None = None


class Approval(Body):
    change_id: Identifier


class Extra(Body):
    description: Text
    amount: Amount


class ExtraId(Body):
    extra_id: Identifier


class ExtraPayment(Reference):
    extra_id: Identifier
    method: Annotated[str, Field(pattern="^(TRANSFERENCIA|TERMINAL)$")]


class Closure(Body):
    act: Text


class Reason(Body):
    reason: Text


class Rejection(Reason):
    change_id: Identifier


class SupplierAssignment(Body):
    supplier_id: Identifier
    service: Text
    cost: Amount
    replaces: Identifier | None = None


class Response(Body):
    accepted: Annotated[bool, Field(strict=True)]
