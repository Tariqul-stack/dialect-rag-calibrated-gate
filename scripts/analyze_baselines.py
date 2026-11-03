"""Compare the calibrated gate against baselines on the dev `val` split.
B0  always answer (no gate)
B1  retrieval-score threshold (cosine(query, passage), multilingual-e5-large) -> answer / cannot_answer only
B2  same decomposed gate, but Qwen2.5 (0.5B / 1.5B) as the scorer instead of d1; also Qwen 5-way `action` raw
B3  d1 5-way `action` question (undecomposed);  OURS = d1 decomposed + temperature scaling + grounding
Thresholds / temperatures are always fit on `fit` only. Usage:
  python scripts/analyze_baselines.py [--d1 CSV] [--sim CSV] [--qwen05 CSV] [--qwen15 CSV]
Missing optional files are skipped."""
import argparse, json, sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aisis import paths
from aisis.gate.calibration import ece, temp
from aisis.gate.decision import run
from aisis.gate.metrics import aurc, auroc, best_thr, metrics
from aisis.gate.selection import fit_config

B = paths.RESULTS / "baselines"
ap = argparse.ArgumentParser()
ap.add_argument("--d1", default=str(paths.RESULTS / "gate_dev" / "results_d1_dev_gate-v2.csv"))
ap.add_argument("--sim", default=str(B / "retrieval_score_mE5large.csv"))
ap.add_argument("--qwen05", default=str(B / "results_qwen0.5b.csv"))
ap.add_argument("--qwen15", default=str(B / "results_qwen1.5b.csv"))
ap.add_argument("--out", default=str(B / "summary_val.csv"))
a = ap.parse_args()

dev = pd.read_excel(paths.DEV_XLSX, sheet_name="DevSet").fillna("")
meta = dev[["dev_id", "split", "query_standard", "query_dialect_synth"]]


def load(csv):
    d = pd.read_csv(csv).merge(meta, on="dev_id")
    d["query"] = np.where(d.version == "dialect", d.query_dialect_synth, d.query_standard)
    for q in ["supported", "emergency", "tool", "action"]:
        d[f"P_{q}"] = d[f"probs_{q}"].apply(json.loads)
    return d


rows, sup = [], []


def add(name, m, extra=None):
    r = dict(system=name, action_acc=round(m["acc"], 3), missed_emergency=f'{m["missed"]}/{m["n_hr"]}',
             over_triage=f'{m["over"]}/{m["n_over"]}', wrong_tool_exec=f'{m["wrong_tool"]}/{m["executed"]}',
             wrong_answers=m["bad_answers"])
    r.update(extra or {})
    rows.append(r)


def mm(df, pred):
    m = metrics(df, pred)
    m["n_hr"] = int(((df.type == "high_risk") & (df.version != "wrong_passage")).sum())
    return m


d1 = load(a.d1)
val1 = d1[d1.split == "val"]

# ---- B0: always answer
add("B0 always answer (no gate)", mm(val1, ["answer_from_passage"] * len(val1)))

# ---- B1: retrieval score
if Path(a.sim).exists():
    s = pd.read_csv(a.sim).merge(d1[["dev_id", "version", "split", "gold_supported", "gold_action", "type", "pred_tool", "gold_tool"]],
                                 on=["dev_id", "version"])
    fit_s, val_s = s[s.split == "fit"], s[s.split == "val"]
    thr = best_thr(fit_s.sim.to_numpy(), (fit_s.gold_supported == "supported").to_numpy())
    pred = np.where(val_s.sim >= thr, "answer_from_passage", "cannot_answer")
    add(f"B1 retrieval-score (tau={thr:.3f}); cannot detect emergency/tool", mm(val_s, pred))
    sup.append(("B1 cosine score", val_s.sim.to_numpy(), (val_s.gold_supported == "supported").to_numpy(), thr, fit_s))
else:
    print("skip B1 (no sim csv)")

# ---- B3 and OURS
add("B3 d1 5-way action", mm(val1.assign(), val1.pred_action.tolist()))
fit1 = d1[d1.split == "fit"]
cfg1, miss_fit1 = fit_config(fit1)
add("OURS d1 decomposed + calibration + grounding", mm(val1, run(val1, cfg1["te"], cfg1["ts"], cfg1["tt"], cfg1["T"])),
    dict(fit_missed=miss_fit1))

# ---- B2 Qwen (scorer swap) ----
scorers = [("d1-3B", d1, cfg1)]
for nm, f in [("Qwen2.5-0.5B", a.qwen05), ("Qwen2.5-1.5B", a.qwen15)]:
    if not Path(f).exists():
        print(f"skip {nm} (no csv)"); continue
    q = load(f); v = q[q.split == "val"]; ft = q[q.split == "fit"]
    add(f"B2 {nm} 5-way action (raw)", mm(v, v.pred_action.tolist()))
    cfg, mf = fit_config(ft)
    add(f"B2 {nm} decomposed + calibration + grounding", mm(v, run(v, cfg["te"], cfg["ts"], cfg["tt"], cfg["T"])), dict(fit_missed=mf))
    scorers.append((nm, q, cfg))

# ---- supported-detection quality: AUROC / risk-coverage / ECE (val) ----
det = []
for nm, df, cfg in scorers:
    v, ft = df[df.split == "val"], df[df.split == "fit"]
    for tag, T in [("raw", 1.0), ("scaled", cfg["T"]["supported"])]:
        pv = np.array([temp(p, T)["supported"] for p in v.P_supported]); pf = np.array([temp(p, T)["supported"] for p in ft.P_supported])
        pos = (v.gold_supported == "supported").to_numpy()
        thr = best_thr(pf, (ft.gold_supported == "supported").to_numpy())
        conf = np.maximum(pv, 1 - pv); ok = (pv >= .5) == pos
        det.append(dict(scorer=f"{nm} P(supported) {tag}", AUROC=round(auroc(pv, pos), 3), AURC=round(aurc(pv, pos), 3),
                        ECE=round(ece(conf, ok), 3), acc_at_fit_thr=round(float(((pv >= thr) == pos).mean()), 3),
                        false_accept=int(((pv >= thr) & ~pos).sum())))
for nm, score, pos, thr, ft in sup:
    det.append(dict(scorer=nm, AUROC=round(auroc(score, pos), 3), AURC=round(aurc(score, pos), 3), ECE=np.nan,
                    acc_at_fit_thr=round(float(((score >= thr) == pos).mean()), 3), false_accept=int(((score >= thr) & ~pos).sum())))

R = pd.DataFrame(rows)
pd.set_option("display.width", 250, "display.max_colwidth", 70)
print(f"== VAL (n={len(val1)}): full decision ==\n", R.to_string(index=False))
print("\n== VAL: how well each score separates 'passage supports the answer' (higher AUROC / lower AURC is better) ==\n", pd.DataFrame(det).to_string(index=False))
R.to_csv(a.out, index=False)
pd.DataFrame(det).to_csv(str(a.out).replace(".csv", "_supported.csv"), index=False)
