from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.domain.errors import BusinessError, Conflict
from src.domain.event import Event
from src.domain.policies import ChangePolicy
from src.domain.proposal import Proposal
from src.domain.specifications import CAN_CLOSE, CAN_SEND, Specification
from src.domain.state_machine import EVENT_TRANSITIONS, next_state
from src.domain.supplier import SupplierRequest
from src.domain.value_objects import Line, Money, amount


def event():
    result = Event("E1", "C1", "2026-12-06", "Boda", 100, "1000")
    result.accept()
    result.sign("CONTRATO", "2026-11-06T18:00:00+00:00", "C1")
    return result


@pytest.mark.parametrize("value", ["-1", "NaN", "Infinity", "abc", None])
def test_money_rejects_invalid(value):
    with pytest.raises(BusinessError):
        Money(value)


def test_money_rounding_and_currency():
    assert amount("1.005") == Decimal("1.01")
    with pytest.raises(BusinessError):
        Money(1, "USD")


@pytest.mark.parametrize("quantity", [0, -1, True, 1.5])
def test_positive_integer_quantity(quantity):
    with pytest.raises(BusinessError):
        Line("P1", "Servicio", quantity, Money(10))


def test_line_roundtrip():
    line = Line("P1", "Servicio", 3, Money("10.01"))
    assert Line.from_dict(line.to_dict()).subtotal == Decimal("30.03")


@pytest.mark.parametrize(
    "paid,state", [("299.99", "ACEPTADO"), ("300.00", "CONFIRMADO"), ("300.01", "CONFIRMADO")]
)
def test_BR01_30_percent_boundary(paid, state):
    item = event()
    item.pay(paid, "P1", "TRANSFERENCIA", "now")
    assert item.state == state


def test_partial_payments_duplicate_and_overpayment():
    item = event()
    item.pay("100", "P1", "EFECTIVO", "now")
    item.pay("200", "P2", "TERMINAL", "now")
    assert item.state == "CONFIRMADO"
    with pytest.raises(Conflict):
        item.pay("1", "P1", "TERMINAL", "now")
    for value, method in [("0", "EFECTIVO"), ("701", "EFECTIVO"), ("10", "CRIPTO")]:
        with pytest.raises(BusinessError):
            item.pay(value, "P3", method, "now")


def test_payment_and_contract_requirements():
    item = Event("E1", "C1", "2026-12-06", "Boda", 1, "1000")
    with pytest.raises(Conflict):
        item.pay(1, "P1", "TERMINAL", "now")
    with pytest.raises(Conflict):
        item.sign("C", "now", "C1")
    item.accept()
    with pytest.raises(BusinessError):
        item.pay(1, "P1", "TERMINAL", "now")
    item.sign("C", "now", "C1")
    with pytest.raises(Conflict):
        item.sign("C2", "now", "C1")


@pytest.mark.parametrize(
    "days,charge,late",
    [(16, "0.00", False), (15, "0.00", False), (14, "15.00", True), (0, "15.00", True)],
)
def test_BR03_BR04_fifteen_days(days, charge, late):
    today = date(2026, 11, 6)
    result = ChangePolicy().evaluate(today + timedelta(days=days), today, "100")
    assert result["charge"] == charge
    assert result["late"] is late


def test_change_after_event_rejected():
    with pytest.raises(BusinessError):
        ChangePolicy().evaluate(date(2026, 11, 5), date(2026, 11, 6), 100)


def test_proposal_states_and_immutable_history():
    p = Proposal("E1", "E1")
    with pytest.raises(BusinessError):
        _ = p.current
    first = p.revise([Line("P1", "Salón", 1, Money(100))], "now", "coord", "Inicial")
    first["total"] = "999"
    assert p.current["total"] == "100.00"
    p.revise([Line("P1", "Salón", 1, Money(200))], "now", "coord", "Ajuste")
    assert p.versions[0]["total"] == "100.00"
    assert Proposal.from_dict(p.to_dict()).current["number"] == "1.1"
    with pytest.raises(Conflict):
        p.accept()
    with pytest.raises(BusinessError):
        p.send(False, True)
    p.send(True, True)
    with pytest.raises(Conflict):
        p.send(True, True)
    with pytest.raises(Conflict):
        p.revise([], "now", "coord", "No permitido")
    p.accept()
    with pytest.raises(Conflict):
        p.accept()


@pytest.mark.parametrize(
    "active,lines,authorized",
    [(False, [1], True), (True, [], True), (True, [1], False), (True, [1], True)],
)
def test_specifications_and(active, lines, authorized):
    assert CAN_SEND.is_satisfied_by(locals()) == (active and bool(lines) and authorized)


@pytest.mark.parametrize("balance,complete", [(0, True), (1, True), (0, False), (1, False)])
def test_specifications_or_not(balance, complete):
    assert CAN_CLOSE.is_satisfied_by(locals()) == (balance == 0 and complete)


def test_abstract_specification():
    with pytest.raises(NotImplementedError):
        Specification().is_satisfied_by({})


@pytest.mark.parametrize("current", list(EVENT_TRANSITIONS))
@pytest.mark.parametrize("target", list(EVENT_TRANSITIONS))
def test_full_event_transition_table(current, target):
    if target in EVENT_TRANSITIONS[current]:
        assert next_state(current, target) == target
    else:
        with pytest.raises(Conflict):
            next_state(current, target)


@pytest.mark.parametrize(
    "offset,valid",
    [
        (timedelta(hours=48) - timedelta(microseconds=1), True),
        (timedelta(hours=48), False),
        (timedelta(hours=49), False),
    ],
)
def test_BR02_continuous_hours(offset, valid):
    now = datetime(2026, 11, 6, 18, tzinfo=timezone.utc)
    request = SupplierRequest("S1", "E1", "P1", "Salón", "100", now.isoformat())
    if valid:
        request.respond(True, now + offset)
        assert request.state == "CONFIRMADO"
    else:
        with pytest.raises(BusinessError):
            request.respond(True, now + offset)
        assert request.expire(now + offset)
        assert not request.expire(now + offset)


def test_supplier_rejection_cancel_roundtrip():
    now = datetime.now(timezone.utc)
    request = SupplierRequest("S1", "E1", "P1", "Salón", "100", now.isoformat())
    assert not request.expire(now)
    request.respond(False, now)
    with pytest.raises(Conflict):
        request.respond(True, now)
    with pytest.raises(Conflict):
        request.cancel("Cancelado", now)
    request.state = "CONFIRMADO"
    request.cancel("Fuerza mayor", now)
    assert SupplierRequest.from_dict(request.to_dict()).state == "CANCELADO"


def test_BR05_BR08_extra_requires_payment_and_trace():
    item = event()
    item.pay(1000, "TOTAL", "TRANSFERENCIA", "now")
    item.start(date(2026, 12, 6), True)
    item.add_extra("X1", "Música", 100, "now")
    with pytest.raises(BusinessError):
        item.deliver_extra("X1", "now")
    with pytest.raises(BusinessError):
        item.finish()
    with pytest.raises(BusinessError):
        item.pay_extra("X1", "EXTRA", "EFECTIVO", "now")
    item.pay_extra("X1", "EXTRA", "TERMINAL", "now")
    with pytest.raises(Conflict):
        item.pay_extra("X1", "EXTRA-2", "TERMINAL", "now")
    item.deliver_extra("X1", "now")
    with pytest.raises(Conflict):
        item.deliver_extra("X1", "now")
    item.finish()
    item.close("ACTA-01", "now", "coord")
    assert item.balance == 0
    assert item.state == "CERRADO"


def test_BR09_start_close_blocks_and_validation():
    item = event()
    with pytest.raises(BusinessError):
        item.start(date(2026, 12, 5), True)
    with pytest.raises(BusinessError):
        item.start(date(2026, 12, 6), False)
    with pytest.raises(BusinessError):
        item.close("ACTA", "now", "coord")
    with pytest.raises(BusinessError):
        item.add_extra("X1", "", 10, "now")
    with pytest.raises(BusinessError):
        item.get_extra("missing")
    item.pay(1000, "TOTAL", "TERMINAL", "now")
    with pytest.raises(BusinessError):
        item.start(date(2026, 12, 6), False)
    for guests in [0, -1, True, 1.5]:
        with pytest.raises(BusinessError):
            Event("E2", "C1", "2026-12-06", "Boda", guests, 100)


def test_change_invariants_and_serialization():
    item = event()
    with pytest.raises(Conflict):
        item.request_change("C1", {"guests": 2}, {}, "now", "coord")
    item.pay(300, "P1", "TERMINAL", "now")
    for data in [{"increment": 1}, {"guests": 0}, {"menu": ""}]:
        with pytest.raises(BusinessError):
            item.request_change("C1", data, {}, "now", "coord")
    evaluation = {"late": True, "charge": "15.00"}
    item.request_change("C1", {"guests": 110, "increment": "100"}, evaluation, "now", "coord")
    with pytest.raises(Conflict):
        item.request_change("C2", {"guests": 120}, {}, "now", "coord")
    with pytest.raises(BusinessError):
        item.apply_change("missing", "now", "admin")
    item.apply_change("C1", "now", "admin")
    assert item.total == "1115.00"
    assert item.guests == 110
    with pytest.raises(Conflict):
        item.apply_change("C1", "now", "admin")
    assert Event.from_dict(item.to_dict()).changes[0]["approved_by"] == "admin"
