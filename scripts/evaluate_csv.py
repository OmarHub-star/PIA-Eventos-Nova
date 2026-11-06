"""Ejecuta 120 casos y 20 transiciones; registra adaptaciones al BRD del equipo."""

import csv
import sys
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.domain.errors import BusinessError, Conflict  # noqa: E402
from src.domain.event import Event  # noqa: E402
from src.domain.proposal import Proposal  # noqa: E402
from src.domain.specifications import CAN_SEND  # noqa: E402
from src.domain.value_objects import Line, Money  # noqa: E402
from src.infrastructure.fixtures import rows  # noqa: E402


def contexts():
    actors = {r["actor_id"]: r for r in rows("actores.csv")}
    catalog = {r["recurso_id"]: r for r in rows("catalogo.csv")}
    details = rows("detalle_operaciones.csv")
    result = {}
    for operation in rows("operaciones.csv"):
        detail = [d for d in details if d["operacion_id"] == operation["operacion_id"]]
        lines = [
            Line(
                d["recurso_id"],
                catalog[d["recurso_id"]]["descripcion"],
                int(d["cantidad"]),
                Money(catalog[d["recurso_id"]]["precio_mxn"]),
            )
            for d in detail
        ]
        # Oráculo financiero independiente: centavos enteros, sin usar Event.total.
        cents = sum(
            int(Decimal(catalog[d["recurso_id"]]["precio_mxn"]) * 100) * int(d["cantidad"])
            for d in detail
        )
        result[operation["operacion_id"]] = {
            "operation": operation,
            "lines": lines,
            "cents": cents,
            "active": actors[operation["actor_id"]]["activo"] == "1",
            "authorized": operation["autorizado"] == "1",
        }
    return result


def draft(context):
    operation = context["operation"]
    proposal = Proposal(operation["operacion_id"], operation["operacion_id"])
    version = proposal.revise(context["lines"], "2026-11-06T18:00:00+00:00", "CSV", "Caso adaptado")
    event = Event(
        operation["operacion_id"],
        operation["actor_id"],
        "2026-11-06",
        "Prueba CSV",
        1,
        version["total"],
    )
    return event, proposal


def advance(context):
    event, proposal = draft(context)
    event.accept()
    event.sign("CONTRATO-PRUEBA", "2026-11-06T18:00:00+00:00", "CSV")
    value = (Decimal(context["cents"]) / 100 * Decimal("0.30")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    try:
        event.pay(value, "PAGO-PRUEBA", "TRANSFERENCIA", "2026-11-06T18:00:00+00:00")
        observed = event.state
    except BusinessError:
        observed = "RECHAZADO"
    expected = "CONFIRMADO" if (context["cents"] * 30 + 50) // 100 > 0 else "RECHAZADO"
    return expected, observed


def evaluate_case(case, context):
    if case["tipo_prueba"] == "validar_operacion":
        expected = context["active"] and context["authorized"] and len(context["lines"]) > 0
        observed = CAN_SEND.is_satisfied_by(context)
        rule = "Precondiciones diagnósticas AND. autorizado CSV no sustituye autenticación."
        status = "CONSERVADO_DIAGNOSTICO"
    else:
        expected, observed = advance(context)
        rule = "BR01: contrato y anticipo 30%. Sustituye VIP, ajeno al BRD."
        status = "ADAPTADO_BRD"
    return {
        "caso_id": case["caso_id"],
        "operacion_id": case["operacion_id"],
        "tratamiento": status,
        "regla_ejecutada": rule,
        "esperado": str(expected),
        "observado": str(observed),
        "resultado_alumno": "PASS" if expected == observed else "FAIL",
    }


def evaluate_transition(case, context):
    event, proposal = draft(context)
    action = case["accion_sugerida"]
    expected = {
        "cancelar": "CANCELADO",
        "repetir_aprobacion": "CONFLICTO",
        "saltar_estado": "CONFLICTO",
        "aprobar": "ACEPTADO",
        "completar": "CERRADO",
    }[action]
    eligible = context["active"] and context["authorized"] and bool(context["lines"])
    if action in {"aprobar", "completar", "repetir_aprobacion"} and not eligible:
        expected = "RECHAZADO"
    if action == "completar" and context["cents"] == 0:
        expected = "RECHAZADO"
    try:
        if action == "cancelar":
            event.cancel("Cancelación de prueba")
        elif action == "saltar_estado":
            event.finish()
        else:
            proposal.send(context["active"], context["authorized"])
            proposal.accept()
            event.accept()
            if action == "repetir_aprobacion":
                event.accept()
            elif action == "completar":
                event.sign("CONTRATO-PRUEBA", "now", "CSV")
                event.pay(event.total, "TOTAL-PRUEBA", "TRANSFERENCIA", "now")
                event.start(date(2026, 11, 6), suppliers_ready=True)
                event.finish()
                event.close("ACTA-PRUEBA", "now", "CSV")
        observed = event.state
    except Conflict:
        observed = "CONFLICTO"
    except BusinessError:
        observed = "RECHAZADO"
    return {
        "caso_id": case["caso_id"],
        "operacion_id": case["operacion_id"],
        "accion_sugerida": action,
        "estado_original": case["estado_inicial"],
        "estado_inicial_adaptado": "BORRADOR",
        "esperado": expected,
        "observado": observed,
        "resultado_alumno": "PASS" if expected == observed else "FAIL",
        "nota": "Precondiciones sintéticas explícitas de contrato/pago/proveedor en completar. API probada por suite de integración.",
    }


def write_csv(path, values):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(values[0]))
        writer.writeheader()
        writer.writerows(values)


def main():
    data = contexts()
    case_results = [evaluate_case(c, data[c["operacion_id"]]) for c in rows("casos_prueba.csv")]
    transitions = [
        evaluate_transition(c, data[c["operacion_id"]]) for c in rows("transiciones_prueba.csv")
    ]
    destination = ROOT / "docs" / "evidencias"
    destination.mkdir(parents=True, exist_ok=True)
    write_csv(destination / "resultados_120_casos.csv", case_results)
    write_csv(destination / "resultados_20_transiciones.csv", transitions)
    failures = [r for r in case_results + transitions if r["resultado_alumno"] != "PASS"]
    print(f"Casos: {len(case_results)}. Transiciones: {len(transitions)}. Fallos: {len(failures)}.")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
