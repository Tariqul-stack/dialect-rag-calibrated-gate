"""Summarise retrieval baselines (R@1, R@5, MRR) per model / version / split."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aisis import paths

r = pd.read_csv(paths.RESULTS / "retrieval" / "ranks_baselines.csv")
meta = pd.read_csv(paths.RESULTS / "retrieval" / "retrieval_meta_baselines.csv").set_index("model")
r["r1"], r["r5"], r["rr"] = (r["rank"] <= 1), (r["rank"] <= 5), 1 / r["rank"]
f = lambda d: pd.Series(dict(n=len(d), R1=d.r1.mean(), R5=d.r5.mean(), MRR=d.rr.mean()))
print("== fit split, dialect queries whose text differs from standard (n=72; model-selection subset)"); print(r[(r.split == "fit") & (r.version == "dialect") & (r.differs == "yes")].groupby("model").apply(f).round(3).sort_values("R1", ascending=False))
print("== all dev, dialect text differs"); print(r[(r.version == "dialect") & (r.differs == "yes")].groupby("model").apply(f).round(3).sort_values("R1", ascending=False))
print("== standard vs dialect (all)"); print(r.groupby(["model", "version"]).apply(f).round(3))
print("== compute (Kaggle T4 batch numbers, NOT edge profiling)"); print(meta.round(2))
