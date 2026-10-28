# Experiment log

All numbers below are reproducible from files in `results/` via `scripts/`.

## E1 – Pilot: d1-3B vs Laya (60 rows → 144 instances)
`results/gate_pilot/`, notebooks 01/02. Questions: `gate_questions_v1.json`.
- d1 5-way action acc: standard 0.633 / dialect 0.600 / wrong-passage 0.833; emergency 6/6; tool 0.83 / 0.75.
- Laya: 5-way 0.18 / 0.20; emergency 2/6 and 0/6. → Laya demoted to baseline.
- Decomposed rule on pilot: d1 0.80 / 0.70 (variant chosen after looking at pilot → **exploratory only**).

## E2 – Dev set, d1 gate v1 (emergency wording v1)
`results/gate_dev/results_d1_dev_gate-v1.csv`: acc 0.83; 2 missed emergencies (one animal bite); over-triage 9/216.

## E3 – Dev set, d1 gate v2 (reworded emergency question) — **frozen**
`results/gate_dev/results_d1_dev_gate-v2.csv`, `python scripts/analyze_gate.py`.
- Fit temperatures: supported 0.4, emergency 0.3, tool 0.9; thresholds 0.1 / 0.7 / 0.5.
- **val**: action acc 0.865 (CI 0.813–0.915) vs 5-way 0.733; missed emergency 0/24; over-triage 2/216; wrong executed tool 0/42; answerable 0.93; high-risk 1.00; tool 0.88; unanswerable 0.78; wrong-passage 0.92; ambiguous 0.61.
- Calibration (val): supported ECE 0.107→0.019; emergency 0.041→0.008; tool 0.047→0.038 (no real gain).
- Note: an earlier chat summary quoted supported ECE 0.014; the committed script gives 0.019 — **use 0.019**.

## E4 – Retrieval baselines (KB = 136 passages; 1000 query instances in `ranks_baselines.csv`)
`results/retrieval/`, `python scripts/analyze_retrieval.py`, notebook 03.
- fit split, dialect-differs (n=72), R@1: mE5-large 0.931, bge-m3 0.889, bangla-e5-small(prefix) 0.778, mE5-small 0.736.
- All dev, dialect-differs (n=108), R@1: 0.944 / 0.917 / 0.824 / 0.787.
- Standard vs dialect R@1 equal within noise for every model → dev dialect text too mild to show a dialect effect.
- Compute (Kaggle T4, batch): not edge profiling.

## Not done yet
Own-model retrieval row; Qwen generator + full pipeline; native-speaker test; edge numbers; paper text.
