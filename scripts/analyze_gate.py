"""Fit temperatures + thresholds on the dev `fit` split, report on `val`.
Usage: python scripts/analyze_gate.py [results_csv] [--out configs/gate_selected.json]
Never touches the native test set."""
import argparse, itertools, json, sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aisis import paths
from aisis.gate.calibration import ece, fit_temperature, temp, nll
from aisis.gate.decision import FROZEN, run
from aisis.gate.metrics import bootstrap_ci, metrics

ap = argparse.ArgumentParser()
ap.add_argument("results", nargs="?", default=str(paths.RESULTS / "gate_dev" / "results_d1_dev_gate-v2.csv"))
ap.add_argument("--out", default=None)
a = ap.parse_args()

dev = pd.read_excel(paths.DEV_XLSX, sheet_name="DevSet").fillna("")
meta = dev[["dev_id", "split", "dialect_differs", "dialect_method", "source", "query_standard", "query_dialect_synth"]]
d = pd.read_csv(a.results).merge(meta, on="dev_id")
d["query"] = np.where(d.version == "dialect", d.query_dialect_synth, d.query_standard)
for q in ["supported", "emergency", "tool", "action"]:
    d[f"P_{q}"] = d[f"probs_{q}"].apply(json.loads)
fit, val = d[d.split == "fit"], d[d.split == "val"]

Ts = {q: fit_temperature(fit[f"P_{q}"], fit[f"gold_{q}"]) for q in ["supported", "emergency", "tool"]}
print("fitted temperatures:", Ts)
for q in Ts:
    for name, T in [("raw", 1.0), ("scaled", Ts[q])]:
        pp = [temp(p, T) for p in val[f"P_{q}"]]
        conf = [max(x.values()) for x in pp]; pred = [max(x, key=x.get) for x in pp]
        ok = [p == g for p, g in zip(pred, val[f"gold_{q}"])]
        print(f"  {q:10s} {name:6s} acc={np.mean(ok):.3f} ECE={ece(conf, ok):.3f} NLL={nll(val[f'P_{q}'], val[f'gold_{q}'], T):.3f}")

grid, tgrid, rows = [.05, .1, .2, .3, .4, .5, .6, .7, .8, .9], [.3, .4, .5, .6, .7, .8], []
for te, ts, tt in itertools.product(grid, grid, tgrid):
    m = metrics(fit, run(fit, te, ts, tt, Ts))
    rows.append(dict(te=te, ts=ts, tt=tt, macro=m["macro"], acc=m["acc"], missed=m["missed"]))
S = pd.DataFrame(rows)
sel = S[S.missed == 0].sort_values(["macro", "acc"], ascending=False).iloc[0]
cfg = dict(T=Ts, te=float(sel.te), ts=float(sel.ts), tt=float(sel.tt))
print("selected on fit:", cfg, "| frozen config:", FROZEN, "| match:", cfg == FROZEN)
if a.out:
    Path(a.out).write_text(json.dumps(cfg, indent=1))

pred = run(val, cfg["te"], cfg["ts"], cfg["tt"], Ts)
m = metrics(val, pred)
print("VAL:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items() if k != "by"}, m["by"])
print("5-way action acc on val:", round((val.pred_action == val.gold_action).mean(), 3))
print("bootstrap 95% CI acc:", bootstrap_ci(val.assign(pred=pred)))
