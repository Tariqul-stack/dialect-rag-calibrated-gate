"""Decomposed gate: emergency -> tool(+grounding) -> supported.
The 5-way `action` question is intentionally NOT used (kept only as an ablation)."""
import json
from pathlib import Path

from .calibration import temp
from .grounding import grounded

FROZEN = {"T": {"supported": 0.4, "emergency": 0.3, "tool": 0.9}, "te": 0.1, "ts": 0.7, "tt": 0.5}


def load_config(path=None):
    return json.loads(Path(path).read_text()) if path else dict(FROZEN)


def decide(row, te, ts, tt, Tq):
    pe = temp(row.P_emergency, Tq["emergency"])["emergency"]
    if pe >= te:
        return "refer_to_clinic"
    pt = temp(row.P_tool, Tq["tool"])
    tool = max(pt, key=pt.get)
    if tool != "none" and pt[tool] >= tt:
        return "call_tool" if grounded(tool, row.query) else "ask_clarification"
    ps = temp(row.P_supported, Tq["supported"])["supported"]
    return "answer_from_passage" if ps >= ts else "cannot_answer"


def run(df, te, ts, tt, Tq):
    return [decide(r, te, ts, tt, Tq) for r in df.itertuples()]
