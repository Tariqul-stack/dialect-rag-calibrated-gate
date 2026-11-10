"""Query-only emergency check (revision round 2, reviewer comment 4).

Compares three emergency rules inside the otherwise FROZEN gate (tool + grounding + supported unchanged):
  A  passage    : original gate, emergency score sees query + retrieved passage   (frozen T_e = 0.3, tau_e = 0.1)
  B  query_only : emergency score from the query alone (notebook 08)
  C  or_rule    : refer if A or B fires
For B/C the query-only temperature and threshold are fit on the dev `fit` split ONLY, with the same
lexicographic criterion as the original gate (fewest missed emergencies, then macro accuracy, then accuracy).
Nothing is tuned on native data. Native results are post-hoc (revision) and descriptive.

Input : results/query_only/results_query_only_emergency_v1.csv (notebook 08)
        results/gate_dev/results_d1_dev_gate-v2.csv, results/native/results_native_v1.csv
Output: results/query_only/summary_query_only.csv, results/query_only/emergency_scores_query_only.csv
Usage : python scripts/analyze_query_only.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aisis import paths
from aisis.gate.calibration import fit_temperature, temp
from aisis.gate.decision import load_config
from aisis.gate.grounding import grounded
from aisis.gate.metrics import auroc, metrics

CFG = load_config(paths.ROOT / "configs" / "gate_frozen.json")
OUT = paths.RESULTS / "query_only"
NAT = ["barishal", "chittagong", "rajshahi", "rangpur"]
GRID = [.05, .1, .2, .3, .4, .5, .6, .7, .8, .9]

# ---------- load ----------
Q = pd.read_csv(OUT / "results_query_only_emergency_v1.csv").fillna("")
Q["Pq"] = Q.probs_emergency_q.apply(json.loads)
qd = {(r.source, r.item_id, r.version): r.Pq for r in Q.itertuples()}

dev = pd.read_excel(paths.DEV_XLSX, sheet_name="DevSet").fillna("")
d1 = pd.read_csv(paths.RESULTS / "gate_dev" / "results_d1_dev_gate-v2.csv").fillna("").merge(
    dev[["dev_id", "split", "query_standard", "query_dialect_synth"]], on="dev_id")
d1["query"] = np.where(d1.version == "dialect", d1.query_dialect_synth, d1.query_standard)
# wrong-passage rows reuse the standard query, so they get the standard query-only score
d1["P_q"] = [qd[("dev", r.dev_id, "dialect" if r.version == "dialect" else "standard")] for r in d1.itertuples()]

nat = pd.read_csv(paths.RESULTS / "native" / "results_native_v1.csv").fillna("")
nat["P_q"] = [qd[("native", r.id, r.version)] for r in nat.itertuples()]
nat["gold_emergency"] = np.where(nat.type == "high_risk", "emergency", "not_emergency")

for df in (d1, nat):
    for q in ["supported", "emergency", "tool"]:
        df[f"P_{q}"] = df[f"probs_{q}"].apply(json.loads)


# ---------- gate with a pluggable emergency rule ----------
def decide(row, rule, Tq, tq):
    pe = temp(row.P_emergency, CFG["T"]["emergency"])["emergency"] >= CFG["te"]
    pq = temp(row.P_q, Tq)["emergency"] >= tq if rule != "passage" else False
    fire = {"passage": pe, "query_only": pq, "or_rule": pe or pq}[rule]
    if fire:
        return "refer_to_clinic"
    pt = temp(row.P_tool, CFG["T"]["tool"])
    tool = max(pt, key=pt.get)
    if tool != "none" and pt[tool] >= CFG["tt"]:
        return "call_tool" if grounded(tool, row.query) else "ask_clarification"
    ps = temp(row.P_supported, CFG["T"]["supported"])["supported"]
    return "answer_from_passage" if ps >= CFG["ts"] else "cannot_answer"


def run(df, rule, Tq=1.0, tq=.5):
    return [decide(r, rule, Tq, tq) for r in df.itertuples()]


# ---------- fit query-only temperature + threshold on dev `fit` only ----------
fit = d1[d1.split == "fit"]
Tq = fit_temperature(fit.P_q, fit.gold_emergency)
cand = []
for tq in GRID:
    m = metrics(fit, run(fit, "query_only", Tq, tq))
    cand.append((m["missed"], -m["macro"], -m["acc"], tq))
tq = sorted(cand)[0][3]
print(f"query-only emergency: temperature {Tq} and threshold {tq} fit on dev `fit` (missed on fit: {sorted(cand)[0][0]})")


# ---------- evaluate ----------
def summ(df, name):
    rows = []
    hr = (df.type == "high_risk") & (df.version != "wrong_passage")
    nw = df[df.version != "wrong_passage"]
    pos = (nw.gold_emergency == "emergency").to_numpy()
    pe_p = np.array([temp(p, CFG["T"]["emergency"])["emergency"] for p in nw.P_emergency])
    pe_q = np.array([temp(p, Tq)["emergency"] for p in nw.P_q])
    for rule in ["passage", "query_only", "or_rule"]:
        m = metrics(df, run(df, rule, Tq, tq))
        score = {"passage": pe_p, "query_only": pe_q, "or_rule": np.maximum(pe_p, pe_q)}[rule]
        rows.append(dict(dataset=name, rule=rule, n=len(df), acc=round(m["acc"], 3),
                         missed_emergency=f"{m['missed']}/{int(hr.sum())}", over_triage=f"{m['over']}/{m['n_over']}",
                         wrong_tool=f"{m['wrong_tool']}/{m['executed']}", wrong_answers=m["bad_answers"],
                         emergency_AUROC=round(auroc(score, pos), 3) if 0 < pos.sum() < len(pos) else np.nan,
                         median_P_on_emergencies=round(float(np.median(score[pos])), 3) if pos.any() else np.nan))
    return rows


S = []
S += summ(d1[d1.split == "val"], "dev_val (synthetic)")
r = nat[nat.passage_condition == "retrieved"]
S += summ(r[r.version == "standard"], "native_control (retrieved)")
S += summ(r[r.version.isin(NAT)], "native_dialect (retrieved)")
for v in NAT:
    S += summ(r[r.version == v], f"  {v} (retrieved)")
g = nat[nat.passage_condition == "gold"]
S += summ(g[g.version.isin(NAT)], "native_dialect (gold passage)")
S = pd.DataFrame(S)
pd.set_option("display.width", 230)
print(S.to_string(index=False))
S.to_csv(OUT / "summary_query_only.csv", index=False)

# per-emergency scores on native (which emergencies each rule catches)
e = r[r.type == "high_risk"].copy()
e["P_emerg_passage"] = [round(temp(p, CFG["T"]["emergency"])["emergency"], 4) for p in e.P_emergency]
e["P_emerg_query_only"] = [round(temp(p, Tq)["emergency"], 4) for p in e.P_q]
e = e[["id", "version", "gold_rank", "P_emerg_passage", "P_emerg_query_only"]]
e["caught_passage"] = e.P_emerg_passage >= CFG["te"]
e["caught_query_only"] = e.P_emerg_query_only >= tq
print("\n== Native emergencies (retrieved passage) ==\n", e.to_string(index=False))
e.to_csv(OUT / "emergency_scores_query_only.csv", index=False)
json.dump({"T_query_only": Tq, "tau_query_only": tq, "fit_on": "dev fit split"}, open(OUT / "query_only_config.json", "w"), indent=1)
