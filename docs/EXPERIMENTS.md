# Experiment log

All numbers below are reproducible from files in `results/` via `scripts/`. All results are on the **synthetic dev set**; the native-speaker test set has not been used yet.

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
- Caveat: the emergency wording was revised after seeing one `val` error, so `val` is slightly optimistic.

## E4 – Retrieval baselines (KB = 136 passages; 1000 query instances in `ranks_baselines.csv`)

`results/retrieval/`, `python scripts/analyze_retrieval.py`, notebook 03.

- fit split, dialect-differs (n=72), R@1: mE5-large 0.931, bge-m3 0.889, bangla-e5-small(prefix) 0.778, mE5-small 0.736.
- All dev, dialect-differs (n=108), R@1: 0.944 / 0.917 / 0.824 / 0.787.
- Standard vs dialect R@1 equal within noise for every model → dev dialect text too mild to show a dialect effect.
- Compute (Kaggle T4, batch): not edge profiling.

## E5 – Gate baselines (dev `val`, n = 288 instances)

Question: is the decomposed, calibrated d1 gate needed, or do simpler signals do the job?
Commands: `python scripts/analyze_baselines.py` (single-order Qwen) and, for the debiased Qwen run,
`python scripts/analyze_baselines.py --qwen05 results/baselines/results_qwen0.5b_avg.csv --qwen15 results/baselines/results_qwen1.5b_avg.csv --out results/baselines/summary_val_avg.csv`.
Outputs: `results/baselines/summary_val*.csv`, `summary_val_avg*.csv`. Temperatures and thresholds of every system are fit on `fit` only; for each scorer the fit rule is "fewest missed emergencies on fit, then best macro accuracy".

**Baselines**

| id | system | what it uses |
|---|---|---|
| B0 | always answer | no gate |
| B1 | retrieval-score threshold | cosine(query, passage) from multilingual-e5-large (`query:`/`passage:` prefixes); answer if ≥ τ fit on `fit`; can only answer or abstain (notebook 04) |
| B2 | Qwen2.5-0.5B / 1.5B-Instruct as the scorer | same five typed questions, option letters A, B, C…, probabilities from the first-token logits over the letters (notebook 05: one option order; notebook 06: average over original and reversed order) |
| B3 | d1 5-way `action` question | undecomposed |
| ours | d1 decomposed + temperature scaling + argument grounding | frozen config from E3 |

**Full decision (val, n = 288)**

| system | action acc | missed emergency | over-triage | wrong tool executed | wrong answers |
|---|---|---|---|---|---|
| B0 always answer | 0.333 | 24/24 | 0/216 | – | 192 |
| B1 retrieval score (τ = 0.831) | 0.573 | 24/24 | 0/216 | – | 27 |
| B3 d1 5-way action | 0.733 | **18/24** | 0/216 | 0/14 | 23 |
| **ours (d1 decomposed)** | **0.865** | **0/24** | 2/216 | 0/42 | 5 |
| Qwen2.5-0.5B 5-way, 1 order | 0.167 | 24/24 | 0/216 | 285/288 | 0 |
| Qwen2.5-0.5B decomposed, 1 order | 0.083 | 0/24 | 216/216 | 0/0 | 0 |
| Qwen2.5-1.5B 5-way, 1 order | 0.226 | 9/24 | 12/216 | 157/193 | 0 |
| Qwen2.5-1.5B decomposed, 1 order | 0.191 | 0/24 | 179/216 | 0/8 | 4 |
| Qwen2.5-0.5B 5-way, 2 orders avg | 0.167 | 24/24 | 0/216 | 273/288 | 0 |
| Qwen2.5-0.5B decomposed, 2 orders avg | 0.083 | 0/24 | 216/216 | 0/0 | 0 |
| Qwen2.5-1.5B 5-way, 2 orders avg | 0.274 | 0/24 | 22/216 | 93/120 | 0 |
| Qwen2.5-1.5B decomposed, 2 orders avg | 0.233 | 0/24 | 165/216 | 0/15 | 2 |

**Does the passage support the answer? (val)**

| scorer | AUROC | AURC (lower is better) | ECE raw → scaled | false accepts at fit threshold |
|---|---|---|---|---|
| d1-3B P(supported) | **0.986** | 0.228 | 0.107 → 0.019 | 12 |
| B1 cosine score | 0.944 | 0.254 | – | 17 |
| Qwen2.5-1.5B, 1 order | 0.854 | 0.313 | 0.500 → 0.293 | 16 |
| Qwen2.5-1.5B, 2 orders avg | 0.857 | 0.310 | 0.362 → 0.173 | 42 |
| Qwen2.5-0.5B, 1 order | 0.535 | 0.596 | 0.581 → 0.409 | 1 |
| Qwen2.5-0.5B, 2 orders avg | 0.547 | 0.567 | 0.582 → 0.424 | 0 |

**Emergency and tool questions (val)**

| scorer | emergency AUROC | tool-choice acc on tool rows | predicts "emergency" for (gold 24) |
|---|---|---|---|
| d1-3B | **1.000** | 0.896 | 22/240 |
| Qwen2.5-1.5B, 1 order | 0.898 | 0.938* | 240/240 |
| Qwen2.5-1.5B, 2 orders avg | 0.967 | 0.750 | 240/240 |
| Qwen2.5-0.5B, 1 order | 0.773 | 0.062 | 240/240 |
| Qwen2.5-0.5B, 2 orders avg | 0.776 | 0.312 | 240/240 |

\* Inflated: this Qwen run predicted a tool for most rows, which looks correct on tool rows. Do not report; use the over-triage and wrong-tool counts instead.

**Findings**
- d1's plain 5-way question misses **18/24** emergencies on val; the decomposed gate misses 0/24 at 2/216 over-triage.
- The retrieval score alone is a reasonable detector of "passage supports the answer" (AUROC 0.944) but is worse than d1 (0.986) and cannot detect emergencies or choose tools (24/24 missed).
- Zero-shot Qwen2.5 0.5B/1.5B are not usable gates here. Averaging over option order (position bias) helps 1.5B (emergency AUROC 0.898 → 0.967; decomposed accuracy 0.191 → 0.233) but the gap to d1 remains large. 0.5B is essentially unchanged, so its failure is not position bias.
- Qwen's high over-triage (165–216/216) is not a threshold-grid artefact: extending the grid to 0.9999 changed nothing (tested on the single-order 1.5B run). On `fit`, some true emergencies score below most non-emergencies, so the "no missed emergency on fit" rule forces it to refer nearly everything. d1 separates the classes (lowest gold-emergency score 0.17, highest non-emergency 0.38).

**Caveats**
- One fixed prompt (English instructions, Bengali input), no prompt tuning; the baseline shows that small general-purpose instruction models are not a drop-in gate, not that no LLM can be one (e.g. with fine-tuning).
- Reversing the option order balances only the first and last positions for 5-option questions (`tool`, `action`).
- For the single-order Qwen runs the fitted temperature reached the upper edge (4.0) of the search grid.
- B1 uses the passage given for each dev row (for unanswerable rows this is a topically related but insufficient passage).
- Everything is on the synthetic dev set; native-speaker results are pending.

Files: notebooks `04_baseline_retrieval_score_kaggle`, `05_baseline_qwen_gate_kaggle`, `06_baseline_qwen_gate_debiased_kaggle`; raw outputs `results/baselines/retrieval_score_mE5large.csv`, `results_qwen{0.5b,1.5b}.csv`, `results_qwen{0.5b,1.5b}_avg.csv`.

## E6 – Native-speaker pilot (frozen configuration)
`results/native/`, notebook 07, `python scripts/build_native_set.py`, `python scripts/analyze_native.py`.
- Set: 49 base queries with native renderings (Barishal 40, Chittagong 39, Rajshahi 32, Rangpur 49 = 160 instances) + 49 standard originals as control. 112/160 are verified/corrected LLM drafts; the 48 Chittagong rows were written from scratch. Gold passage for 27 base queries (answerable + high-risk).
- Gate (mE5-large retrieval -> d1-3B, `configs/gate_frozen.json`, nothing tuned): control acc 0.857 (CI 0.755–0.939), 0/4 missed emergency; native pooled acc 0.600 (CI 0.510–0.687), 3/11 missed emergency, over-triage 1/149, wrong tool 0/25, wrong answers 0.
- Per dialect acc: Barishal 0.675, Chittagong 0.333, Rajshahi 0.812, Rangpur 0.612. Retrieval R@1 (27 gold queries): standard 1.000; native 0.700–0.926 (pooled 0.857).
- Over-abstention: 36/73 answerable native queries -> cannot_answer. All 3 missed emergencies occur with a wrong retrieved passage; with the gold passage 0/11 missed.
- Post-hoc diagnostics (descriptive): emergency AUROC 1.000 -> 0.957, answerability AUROC 0.993 -> 0.923; median calibrated P(emergency) on emergencies 0.964 -> 0.325. Ranking survives, calibration does not transfer.
- Caveats: small n, different base queries per dialect, annotation protocol differs (Chittagong from scratch).
