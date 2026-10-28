import sys, types
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aisis.gate.calibration import temp, ece
from aisis.gate.decision import decide, FROZEN
from aisis.gate.grounding import grounded, has_place


def row(pe=0.0, tool="none", pt=0.0, ps=0.9, q="x"):
    return types.SimpleNamespace(
        P_emergency={"emergency": pe, "not_emergency": 1 - pe},
        P_tool={"none": 1 - pt, tool if tool != "none" else "find_nearest_clinic": pt},
        P_supported={"supported": ps, "not_supported": 1 - ps}, query=q)


def run(r):
    return decide(r, FROZEN["te"], FROZEN["ts"], FROZEN["tt"], FROZEN["T"])


def test_temp_normalised():
    assert abs(sum(temp({"a": .7, "b": .3}, .4).values()) - 1) < 1e-9


def test_emergency_wins():
    assert run(row(pe=0.9, ps=0.99)) == "refer_to_clinic"


def test_ungrounded_tool_asks_clarification():
    assert run(row(tool="find_nearest_clinic", pt=0.95, q="কাছের ক্লিনিক কোথায়")) == "ask_clarification"


def test_grounded_tool_called():
    assert run(row(tool="find_nearest_clinic", pt=0.95, q="বরিশাল সদরে ক্লিনিক কোথায়")) == "call_tool"


def test_unsupported_abstains():
    assert run(row(ps=0.2)) == "cannot_answer"


def test_supported_answers():
    assert run(row(ps=0.95)) == "answer_from_passage"


def test_grounding_id_and_place():
    assert grounded("check_service_status", "আবেদন ১২৩৪৫৬") and has_place("ঢাকা")


def test_ece_perfect():
    assert ece([1.0, 1.0], [True, True]) == 0
