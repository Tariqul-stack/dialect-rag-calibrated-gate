"""Native-speaker evaluation with the FROZEN gate configuration (configs/gate_frozen.json); nothing is tuned here.
Input : results/native/results_native_v1.csv (notebook 07).   Output: results/native/summary_native.csv, retrieval_native.csv
Usage : python scripts/analyze_native.py [--csv PATH] [--cfg PATH]"""
import argparse, json, sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aisis import paths
from aisis.gate.decision import load_config, run
from aisis.gate.metrics import metrics

ap = argparse.ArgumentParser()
ap.add_argument("--csv", default=str(paths.RESULTS / "native" / "results_native_v1.csv"))
ap.add_argument("--cfg", default=str(paths.ROOT / "configs" / "gate_frozen.json"))
a = ap.parse_args()
cfg = load_config(a.cfg)
out = Path(a.csv).parent

d = pd.read_csv(a.csv).fillna("")
for q in ["supported", "emergency", "tool"]:
    d[f"P_{q}"] = d[f"probs_{q}"].apply(json.loads)
d["pred"] = run(d, cfg["te"], cfg["ts"], cfg["tt"], cfg["T"])
NAT = ["barishal", "chittagong", "rajshahi", "rangpur"]


def row(name, g):
    m = metrics(g, g.pred.tolist())
    n_hr = int((g.type == "high_risk").sum())
    five = float((g.pred_action == g.gold_action).mean())
    ci = ""
    if g.id.nunique() > 5:
        rng = np.random.default_rng(0); ids = g.id.unique(); by = {i: x for i, x in g.groupby("id")}
        acc = [np.mean(np.concatenate([(by[i].pred == by[i].gold_action).to_numpy() for i in rng.choice(ids, len(ids))])) for _ in range(1000)]
        ci = f"{np.percentile(acc, 2.5):.3f}-{np.percentile(acc, 97.5):.3f}"
    return dict(group=name, n=len(g), base_queries=g.id.nunique(), acc=round(m["acc"], 3), acc_CI95=ci,
                missed_emergency=f"{m['missed']}/{n_hr}", over_triage=f"{m['over']}/{m['n_over']}",
                wrong_tool=f"{m['wrong_tool']}/{m['executed']}", wrong_answers=m["bad_answers"], d1_fiveway_acc=round(five, 3))


rows = []
for cond in ["retrieved", "gold"]:
    c = d[d.passage_condition == cond]
    if c.empty: continue
    base = c[c.version == "standard"]
    rows.append({"passage": cond, **row("standard (control)", base)})
    pooled = c[c.version.isin(NAT)]
    rows.append({"passage": cond, **row("native pooled", pooled)})
    for v in NAT:
        g = c[c.version == v]
        if len(g): rows.append({"passage": cond, **row(v, g)})
S = pd.DataFrame(rows)
pd.set_option("display.width", 250)
print("== Gate with frozen config ==\n", S.to_string(index=False))
S.to_csv(out / "summary_native.csv", index=False)

# retrieval (gold-passage queries only) – use one row per instance from the 'retrieved' condition
r = d[(d.passage_condition == "retrieved") & (d.gold_passage_id != "")]
R = r.groupby("version").apply(lambda g: pd.Series({"n": len(g), "R@1": (g.gold_rank == 1).mean(), "R@3": (g.gold_rank <= 3).mean(),
                                                    "MRR": (1 / g.gold_rank).mean()})).round(3)
R.loc["native pooled"] = [int(r[r.version.isin(NAT)].shape[0])] + [round(x, 3) for x in (
    (r[r.version.isin(NAT)].gold_rank == 1).mean(), (r[r.version.isin(NAT)].gold_rank <= 3).mean(), (1 / r[r.version.isin(NAT)].gold_rank).mean())]
print("\n== Retrieval of the gold passage (answerable + high-risk base queries with a gold passage) ==\n", R.to_string())
R.to_csv(out / "retrieval_native.csv")

# per type, pooled native, retrieved
t = d[(d.passage_condition == "retrieved") & d.version.isin(NAT)]
print("\n== Action accuracy by type, native pooled ==\n", t.assign(ok=t.pred == t.gold_action).groupby("type").ok.agg(["mean", "size"]).round(3).to_string())
print("\n== Confusion (gold -> predicted), native pooled, retrieved ==\n", pd.crosstab(t.gold_action, t.pred).to_string())
