"""Temperature sweep (revision round 2, supervisor suggestion; supports reviewer comments 2/3).

Rescales the stored d1-3B probabilities with a range of temperatures (p^(1/T), renormalized) and reports
  (a) calibration of P(supported) and P(emergency) per data set: ECE and NLL
  (b) gate outcomes when only one temperature is changed and every threshold stays at its frozen value
T = 1 is the raw model output; T -> 0 approaches a hard argmax, so T = 0 itself is undefined (we start at 0.1).
The frozen configuration (T_s = 0.4, T_e = 0.3, T_t = 0.9) is NOT changed: this is a descriptive, post-hoc analysis,
and native results are never used to choose a temperature.

Data sets: synthetic fit and val (dev), native control (standard originals) and native dialect (160 renderings),
native labels derived as in analyze_calibration_native.py.
Output: results/calibration/temperature_sweep_calibration.csv, results/calibration/temperature_sweep_gate.csv,
        results/figures/fig4_temperature_sweep.png
Usage : python scripts/analyze_temperature_sweep.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aisis import paths
from aisis.gate.calibration import ece, nll, temp
from aisis.gate.decision import load_config
from aisis.gate.grounding import grounded
from aisis.gate.metrics import metrics

CFG = load_config(paths.ROOT / "configs" / "gate_frozen.json")
OUT, FIG = paths.RESULTS / "calibration", paths.RESULTS / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
TS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0]
NAT = ["barishal", "chittagong", "rajshahi", "rangpur"]

# ---------- data ----------
dev = pd.read_excel(paths.DEV_XLSX, sheet_name="DevSet").fillna("")
d1 = pd.read_csv(paths.RESULTS / "gate_dev" / "results_d1_dev_gate-v2.csv").fillna("").merge(
    dev[["dev_id", "split", "query_standard", "query_dialect_synth"]], on="dev_id")
d1["query"] = np.where(d1.version == "dialect", d1.query_dialect_synth, d1.query_standard)
nat = pd.read_csv(paths.RESULTS / "native" / "results_native_v1.csv").fillna("")
nat = nat[nat.passage_condition == "retrieved"].copy()
nat["gold_supported"] = np.where((nat.type == "answerable") & (nat.top1_id == nat.gold_passage_id), "supported",
                                 np.where((nat.type == "unanswerable") | ((nat.type == "answerable") & (nat.top1_id != nat.gold_passage_id)),
                                          "not_supported", ""))
nat["gold_emergency"] = np.where(nat.type == "high_risk", "emergency", "not_emergency")
for df in (d1, nat):
    for q in ["supported", "emergency", "tool"]:
        df[f"P_{q}"] = df[f"probs_{q}"].apply(json.loads)

SETS = {"synthetic_fit": d1[d1.split == "fit"], "synthetic_val": d1[d1.split == "val"],
        "native_control": nat[nat.version == "standard"], "native_dialect": nat[nat.version.isin(NAT)]}

# ---------- (a) calibration vs T ----------
rows = []
for name, df in SETS.items():
    for q in ["supported", "emergency"]:
        g = df[df[f"gold_{q}"] != ""]
        y = (g[f"gold_{q}"] == q).to_numpy()
        for T in TS:
            p = np.array([temp(a, T)[q] for a in g[f"P_{q}"]])
            conf = np.maximum(p, 1 - p)
            rows.append(dict(question=q, dataset=name, T=T, n=len(g), ECE=round(ece(conf, (p >= .5) == y), 3),
                             NLL=round(nll(list(g[f"P_{q}"]), list(g[f"gold_{q}"]), T), 3)))
C = pd.DataFrame(rows)
C.to_csv(OUT / "temperature_sweep_calibration.csv", index=False)


# ---------- (b) gate outcomes vs one temperature (thresholds frozen) ----------
def decide(row, Te, Ts):
    if temp(row.P_emergency, Te)["emergency"] >= CFG["te"]:
        return "refer_to_clinic"
    pt = temp(row.P_tool, CFG["T"]["tool"])
    t = max(pt, key=pt.get)
    if t != "none" and pt[t] >= CFG["tt"]:
        return "call_tool" if grounded(t, row.query) else "ask_clarification"
    return "answer_from_passage" if temp(row.P_supported, Ts)["supported"] >= CFG["ts"] else "cannot_answer"


grow = []
for name in ["synthetic_val", "native_dialect"]:
    df = SETS[name]
    n_hr = int(((df.type == "high_risk") & (df.version != "wrong_passage")).sum())
    for vary in ["T_emergency", "T_supported"]:
        for T in TS:
            Te = T if vary == "T_emergency" else CFG["T"]["emergency"]
            Ts = T if vary == "T_supported" else CFG["T"]["supported"]
            m = metrics(df, [decide(r, Te, Ts) for r in df.itertuples()])
            grow.append(dict(dataset=name, varied=vary, T=T, acc=round(m["acc"], 3), missed=m["missed"], n_emergency=n_hr,
                             over_triage=m["over"], n_non_emergency=m["n_over"], wrong_answers=m["bad_answers"]))
G = pd.DataFrame(grow)
G.to_csv(OUT / "temperature_sweep_gate.csv", index=False)

pd.set_option("display.width", 200)
print("== ECE of P(supported) by temperature ==")
print(C[C.question == "supported"].pivot(index="T", columns="dataset", values="ECE").to_string())
print("\n== NLL of P(emergency) by temperature ==")
print(C[C.question == "emergency"].pivot(index="T", columns="dataset", values="NLL").to_string())
for q in ["supported", "emergency"]:
    best = C[C.question == q].loc[lambda x: x.groupby("dataset")["NLL"].idxmin()][["dataset", "T", "NLL", "ECE"]]
    print(f"\nlowest-NLL temperature for P({q}) per data set (descriptive only):\n", best.to_string(index=False))
print("\n== Gate outcomes when one temperature varies (thresholds frozen) ==")
print(G.to_string(index=False))

# ---------- figure ----------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})
COL = {"synthetic_val": "#1f4e9c", "native_control": "#7f7f7f", "native_dialect": "#c0392b"}
LAB = {"synthetic_val": "Synthetic val", "native_control": "Native control", "native_dialect": "Native dialect"}
fig, ax = plt.subplots(1, 2, figsize=(6.4, 2.3))
a = ax[0]
for name in ["synthetic_val", "native_control", "native_dialect"]:
    c = C[(C.question == "supported") & (C.dataset == name)]
    a.plot(c["T"], c.ECE, "o-", c=COL[name], ms=3, lw=1.2, label=LAB[name])
a.axvline(CFG["T"]["supported"], ls=":", c="k", lw=.8)
a.axvline(1.0, ls="--", c="#999", lw=.8)
a.text(CFG["T"]["supported"], .005, " fitted T", fontsize=6.5, va="bottom")
a.text(1.0, .005, " raw (T=1)", fontsize=6.5, va="bottom", color="#666")
a.set_xscale("log"); a.set_xticks(TS[::2] + [1.0]); a.set_xticklabels([str(t) for t in TS[::2] + [1.0]])
a.set(xlabel="Temperature T of P(supported) (log scale)", ylabel="ECE", ylim=(0, .3))
a.set_title("(a) Calibration error of P(supported)", fontsize=8)
a.legend(frameon=False, fontsize=6.5, loc="upper center")
b = ax[1]
g = G[(G.dataset == "native_dialect") & (G.varied == "T_emergency")]
b.plot(g["T"], g.missed, "o-", c="#c0392b", ms=3, lw=1.2, label="Missed emergencies (of 11)")
b2 = b.twinx()
b2.plot(g["T"], g.over_triage, "s--", c="#555", ms=3, lw=1.1, label="Over-triage (of 149)")
b.axvline(CFG["T"]["emergency"], ls=":", c="k", lw=.8)
b.set_xscale("log"); b.set_xticks(TS[::2] + [1.0]); b.set_xticklabels([str(t) for t in TS[::2] + [1.0]])
b.set(xlabel="Temperature T of P(emergency) (log scale)", ylabel="Missed emergencies", ylim=(-.3, 6))
b2.set_ylabel("Over-triage"); b2.set_ylim(-5, 160)
b.set_title("(b) Native dialect: gate outcome vs T", fontsize=8)
h1, l1 = b.get_legend_handles_labels(); h2, l2 = b2.get_legend_handles_labels()
b.legend(h1 + h2, l1 + l2, frameon=False, fontsize=6.5, loc="upper center")
plt.tight_layout()
plt.savefig(FIG / "fig4_temperature_sweep.png", dpi=300)
print("\nwrote", OUT / "temperature_sweep_calibration.csv", "|", OUT / "temperature_sweep_gate.csv", "|", FIG / "fig4_temperature_sweep.png")
