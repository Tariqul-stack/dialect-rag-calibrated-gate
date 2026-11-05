"""Build the native-speaker evaluation set from the filled base-query workbook.
Reads  data/queries/AISIS_Base_Queries_v1.xlsx (Base_Queries) and the gold map in the KB workbook (Paste_Column_I).
Keeps only base queries that have >=1 native-speaker dialect rendering; per base query it emits the standard query
(control) and one row per dialect whose status is native_verified / native_corrected / native_written.
Rows with status 'claude_draft' or empty are excluded. Writes data/native/native_eval_v1.csv.
Usage: python scripts/build_native_set.py"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aisis import paths

DIALECTS = ["barishal", "chittagong", "rajshahi", "rangpur"]   # natore dropped: no native rows
NATIVE = {"native_verified", "native_corrected", "native_written"}
ACTION = {"retrieve_and_answer": "answer_from_passage", "call_tool": "call_tool", "clarify": "ask_clarification",
          "refer_to_clinic": "refer_to_clinic", "abstain": "cannot_answer"}

b = pd.read_excel(paths.QUERIES_XLSX, sheet_name="Base_Queries")
g = pd.read_excel(paths.KB_XLSX, sheet_name="Paste_Column_I").rename(columns={"gold_passage_id": "gold_pid"})
b = b.merge(g, on="id", how="left")
rows = []
for r in b.to_dict("records"):
    nat = [d for d in DIALECTS if r.get(f"{d}_status") in NATIVE and isinstance(r.get(d), str) and r[d].strip()]
    if not nat:
        continue
    base = dict(id=r["id"], type=r["type"], topic=r["topic"], gold_action=ACTION[r["expected_behavior"]],
                gold_tool=r["gold_tool"] if isinstance(r["gold_tool"], str) else "none",
                gold_args=r["gold_args"] if isinstance(r["gold_args"], str) else "",
                gold_passage_id=r["gold_pid"] if isinstance(r["gold_pid"], str) else "")
    rows.append({**base, "version": "standard", "native_status": "", "query": r["standard_query"]})
    for d in nat:
        rows.append({**base, "version": d, "native_status": r[f"{d}_status"], "query": r[d].strip()})
out = pd.DataFrame(rows)
dst = paths.DATA / "native" / "native_eval_v1.csv"
dst.parent.mkdir(exist_ok=True)
out.to_csv(dst, index=False, encoding="utf-8")
nat = out[out.version != "standard"]
print(f"{out.id.nunique()} base queries, {len(nat)} native instances + {(out.version=='standard').sum()} standard controls -> {dst}")
print(nat.groupby("version").size().to_dict())
print(nat.groupby("type").size().to_dict())
print("gold passage available for", (out[out.version == "standard"].gold_passage_id != "").sum(), "base queries")
