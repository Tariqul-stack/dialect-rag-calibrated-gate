"""Fit temperatures + thresholds on the `fit` split for any scorer (d1, Qwen, ...).
Same procedure as scripts/analyze_gate.py; the safety constraint is 'fewest missed emergencies on fit'
(0 for d1; a weak scorer may not reach 0, in which case the lowest count wins)."""
import itertools

import pandas as pd

from .calibration import fit_temperature
from .decision import run
from .metrics import metrics

GRID = [.05, .1, .2, .3, .4, .5, .6, .7, .8, .9]
TOOL_GRID = [.3, .4, .5, .6, .7, .8]


def fit_config(fit):
    Ts = {q: fit_temperature(fit[f"P_{q}"], fit[f"gold_{q}"]) for q in ["supported", "emergency", "tool"]}
    rows = []
    for te, ts, tt in itertools.product(GRID, GRID, TOOL_GRID):
        m = metrics(fit, run(fit, te, ts, tt, Ts))
        rows.append(dict(te=te, ts=ts, tt=tt, macro=m["macro"], acc=m["acc"], missed=m["missed"]))
    S = pd.DataFrame(rows).sort_values(["missed", "macro", "acc"], ascending=[True, False, False])
    sel = S.iloc[0]
    return dict(T=Ts, te=float(sel.te), ts=float(sel.ts), tt=float(sel.tt)), int(sel.missed)
