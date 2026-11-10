"""Calibration of the FROZEN gate on native text (revision round 2, reviewer comments 2/3).

Temperatures come from configs/gate_frozen.json (fit on the dev `fit` split) and are NOT changed here.
We only measure how well the frozen, scaled probabilities are calibrated on three data sets:
  synthetic_val   dev `val` split (synthetic; all versions)          gold labels from the dev set
  native_control  standard-Bengali originals of the 49 native queries   (retrieved passage)
  native_dialect  160 native dialect renderings                         (retrieved passage)

Gold labels on native data (the native set has no per-question labels, so they are derived):
  emergency : positive iff type == high_risk
  supported : positive iff type == answerable and the retrieved top-1 passage is the gold passage;
              negative iff type == unanswerable, or answerable with a wrong top-1 passage;
              tool / ambiguous / high-risk rows are left out (support is not well defined for them)
  tool      : gold_tool (none for non-tool queries)

Outputs
  results/calibration/ece_native.csv               ECE raw/scaled, accuracy, mean confidence, AUROC per question x data set
  results/calibration/class_conditional_native.csv distribution of the calibrated P(positive) per true class
  results/calibration/reliability_native.csv       reliability-diagram bins (scaled)
  results/figures/fig3_native_calibration.png      (a) reliability of P(supported), (b) P(emergency) by class, (c) P(supported) by class
Usage: python scripts/analyze_calibration_native.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aisis import paths
from aisis.gate.calibration import ece, temp
from aisis.gate.decision import load_config
from aisis.gate.metrics import auroc

CFG = load_config(paths.ROOT / "configs" / "gate_frozen.json")
OUT = paths.RESULTS / "calibration"
FIG = paths.RESULTS / "figures"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
NAT = ["barishal", "chittagong", "rajshahi", "rangpur"]


def parse(df):
    for q in ["supported", "emergency", "tool"]:
        df[f"P_{q}"] = df[f"probs_{q}"].apply(json.loads)
    return df


# ---------- data sets with derived binary labels ----------
dev = pd.read_excel(paths.DEV_XLSX, sheet_name="DevSet").fillna("")
d1 = parse(pd.read_csv(paths.RESULTS / "gate_dev" / "results_d1_dev_gate-v2.csv").fillna("").merge(dev[["dev_id", "split"]], on="dev_id"))
val = d1[d1.split == "val"].copy()
val["y_emergency"] = (val.gold_emergency == "emergency").astype(float)
val["y_supported"] = (val.gold_supported == "supported").astype(float)

nat = parse(pd.read_csv(paths.RESULTS / "native" / "results_native_v1.csv").fillna(""))
nat = nat[nat.passage_condition == "retrieved"].copy()
nat["y_emergency"] = (nat.type == "high_risk").astype(float)
sup = np.where((nat.type == "answerable") & (nat.top1_id == nat.gold_passage_id), 1.0,
               np.where((nat.type == "unanswerable") | ((nat.type == "answerable") & (nat.top1_id != nat.gold_passage_id)), 0.0, np.nan))
nat["y_supported"] = sup

SETS = {"synthetic_val": val,
        "native_control": nat[nat.version == "standard"],
        "native_dialect": nat[nat.version.isin(NAT)]}


def scaled(df, q, T):
    return [temp(p, T) for p in df[f"P_{q}"]]


# ---------- ECE / accuracy / AUROC ----------
rows, cls_rows, rel_rows = [], [], []
for name, df in SETS.items():
    for q, pos in [("supported", "supported"), ("emergency", "emergency")]:
        g = df[df[f"y_{q}"].notna()]
        y = g[f"y_{q}"].to_numpy().astype(bool)
        for tag, T in [("raw", 1.0), ("scaled", CFG["T"][q])]:
            p = np.array([s[pos] for s in scaled(g, q, T)])
            conf, ok = np.maximum(p, 1 - p), (p >= .5) == y
            rows.append(dict(question=q, dataset=name, calib=tag, n=len(g), n_pos=int(y.sum()),
                             ECE=round(ece(conf, ok), 3), acc=round(float(ok.mean()), 3),
                             mean_conf=round(float(conf.mean()), 3), AUROC=round(auroc(p, y), 3) if 0 < y.sum() < len(y) else np.nan))
            if tag == "scaled":
                for c, lab in [(True, pos), (False, "not_" + pos)]:
                    v = p[y == c]
                    if len(v):
                        cls_rows.append(dict(question=q, dataset=name, true_class=lab, n=len(v),
                                             mean=round(v.mean(), 3), median=round(float(np.median(v)), 3),
                                             q25=round(float(np.percentile(v, 25)), 3), q75=round(float(np.percentile(v, 75)), 3),
                                             share_above_threshold=round(float((v >= CFG["ts" if q == "supported" else "te"]).mean()), 3)))
                edges = np.linspace(0, 1, 6)
                for lo, hi in zip(edges[:-1], edges[1:]):
                    m = (p >= lo) & ((p < hi) | (hi == 1.0))
                    if m.sum():
                        rel_rows.append(dict(question=q, dataset=name, bin=f"{lo:.1f}-{hi:.1f}", n=int(m.sum()),
                                             mean_pred=round(float(p[m].mean()), 3), frac_pos=round(float(y[m].mean()), 3)))
    # tool (multi-class): confidence = max scaled probability, correct = argmax == gold tool
    g = df
    gold = g.gold_tool.replace("", "none").to_numpy()
    for tag, T in [("raw", 1.0), ("scaled", CFG["T"]["tool"])]:
        s = scaled(g, "tool", T)
        conf = np.array([max(x.values()) for x in s])
        ok = np.array([max(x, key=x.get) == gg for x, gg in zip(s, gold)])
        rows.append(dict(question="tool", dataset=name, calib=tag, n=len(g), n_pos=int((gold != "none").sum()),
                         ECE=round(ece(conf, ok), 3), acc=round(float(ok.mean()), 3), mean_conf=round(float(conf.mean()), 3), AUROC=np.nan))

E = pd.DataFrame(rows)
C = pd.DataFrame(cls_rows)
Rl = pd.DataFrame(rel_rows)
E.to_csv(OUT / "ece_native.csv", index=False)
C.to_csv(OUT / "class_conditional_native.csv", index=False)
Rl.to_csv(OUT / "reliability_native.csv", index=False)
pd.set_option("display.width", 220)
print("== ECE / accuracy / AUROC (frozen temperatures; ECE uses 5 bins over confidence 0.5-1.0) ==")
print(E.pivot_table(index=["question", "dataset"], columns="calib", values=["ECE", "acc", "mean_conf"]).round(3).to_string())
print("\nAUROC (scaled):"); print(E[E.calib == "scaled"].dropna(subset=["AUROC"])[["question", "dataset", "n", "n_pos", "AUROC"]].to_string(index=False))
print("\n== Calibrated P(positive) by true class ==")
print(C.to_string(index=False))

# ---------- figure ----------
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8})
COL = {"synthetic_val": "#1f4e9c", "native_control": "#7f7f7f", "native_dialect": "#c0392b"}
SHORT = {"synthetic_val": "Syn", "native_control": "Ctrl", "native_dialect": "Dial"}
LAB = {"synthetic_val": "Synthetic val", "native_control": "Native control (standard)", "native_dialect": "Native dialect"}
fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.6))
a = ax[0]
a.plot([0, 1], [0, 1], "--", c="#999", lw=.8)
for name in SETS:
    r = Rl[(Rl.question == "supported") & (Rl.dataset == name)]
    a.plot(r.mean_pred, r.frac_pos, "o-", c=COL[name], ms=3, lw=1.1, label=LAB[name])
a.set(xlim=(0, 1), ylim=(0, 1.02), xlabel="Predicted P(supported), scaled", ylabel="Observed fraction supported")
a.set_title("(a) Reliability of P(supported)", fontsize=8)
a.legend(frameon=False, fontsize=6, loc="lower right")


def strip(axis, q, pos, title):
    data, labels, colors = [], [], []
    for name in SETS:
        g = SETS[name][SETS[name][f"y_{q}"].notna()]
        p = np.array([s[pos] for s in scaled(g, q, CFG["T"][q])])
        y = g[f"y_{q}"].to_numpy().astype(bool)
        for c, short in [(True, "pos"), (False, "neg")]:
            data.append(p[y == c]); labels.append(f"{SHORT[name]}\n{short}"); colors.append(COL[name])
    bp = axis.boxplot(data, widths=.55, patch_artist=True, showfliers=False)
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c); patch.set_alpha(.35)
    rng = np.random.default_rng(0)
    for i, (v, c) in enumerate(zip(data, colors), start=1):
        axis.scatter(i + rng.uniform(-.15, .15, len(v)), v, s=4, c=c, alpha=.6, linewidths=0)
    thr = CFG["te"] if q == "emergency" else CFG["ts"]
    axis.axhline(thr, ls=":", c="k", lw=.8)
    axis.set_xticks(range(1, len(labels) + 1)); axis.set_xticklabels(labels, fontsize=6.5)
    axis.set_ylim(-.02, 1.02); axis.set_title(title, fontsize=8)


strip(ax[1], "emergency", "emergency", "(b) P(emergency) by true class")
ax[1].set_ylabel("Calibrated probability")
strip(ax[2], "supported", "supported", "(c) P(supported) by true class")
plt.tight_layout()
plt.savefig(FIG / "fig3_native_calibration.png", dpi=300)
print("\nwrote", OUT / "ece_native.csv", "|", OUT / "class_conditional_native.csv", "|", FIG / "fig3_native_calibration.png")
