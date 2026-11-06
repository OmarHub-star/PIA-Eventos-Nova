from src.domain.errors import Conflict

EVENT_TRANSITIONS = {
    "BORRADOR": {"ACEPTADO", "CANCELADO"},
    "ACEPTADO": {"CONFIRMADO", "CANCELADO"},
    "CONFIRMADO": {"EN_EJECUCION", "CANCELADO"},
    "EN_EJECUCION": {"FINALIZADO"},
    "FINALIZADO": {"CERRADO"},
    "CERRADO": set(),
    "CANCELADO": set(),
}


def next_state(current: str, target: str) -> str:
    if target not in EVENT_TRANSITIONS.get(current, set()):
        raise Conflict(f"Transición inválida: {current} -> {target}")
    return target
