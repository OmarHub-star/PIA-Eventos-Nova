import pytest

from scripts.evaluate_csv import contexts, evaluate_case, evaluate_transition
from src.infrastructure.fixtures import rows

DATA = contexts()
CASES = rows("casos_prueba.csv")
TRANSITIONS = rows("transiciones_prueba.csv")


@pytest.mark.parametrize("case", CASES, ids=[r["caso_id"] for r in CASES])
def test_original_csv_cases_with_documented_adaptation(case):
    result = evaluate_case(case, DATA[case["operacion_id"]])
    assert result["resultado_alumno"] == "PASS", result


@pytest.mark.parametrize("case", TRANSITIONS, ids=[r["caso_id"] for r in TRANSITIONS])
def test_original_csv_transitions_adapted_to_eventos_nova(case):
    result = evaluate_transition(case, DATA[case["operacion_id"]])
    assert result["resultado_alumno"] == "PASS", result
