# Knowing When Not to Act: Calibrated Decision Gating for Dialectal Bengali Retrieval Assistants

> **Status:** paper submitted to AISIS 2027 (under review). Results below cover the synthetic development set **and** a pilot native-speaker evaluation run with a frozen configuration. See [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) for the full experiment log (E1–E6) and [`docs/DATA_CARD.md`](docs/DATA_CARD.md) for data provenance.

## Idea

Assistants for rural Bangladeshi users must (1) understand dialectal Bengali queries, (2) retrieve the right information, and (3) **avoid wrong decisions and wrong tool actions**, on low-compute hardware. The contribution is a **decomposed, temperature-calibrated decision gate** that decides whether the system should answer, call a tool, ask for clarification, refer to a clinic, or abstain. No model is fine-tuned. Evaluation is text-only; voice (ASR/TTS) is out of scope.

```
dialect query -> retriever (multilingual-e5-large) -> top-1 passage over a 136-passage KB
              -> GATE: Liquid AI d1-3B typed questions (emergency, tool, supported, specific)
                       + temperature scaling + rule-based argument grounding
              -> answer_from_passage | call_tool | ask_clarification | refer_to_clinic | cannot_answer
```

Gate order (first case that applies): (1) emergency, recall-first (τe = 0.1) → `refer_to_clinic`; (2) tool needed (τt = 0.5) and its arguments (place / crop / date / id) present in the query → `call_tool`, otherwise `ask_clarification`; (3) calibrated `supported` probability (τs = 0.7) → `answer_from_passage` or `cannot_answer`. Temperatures (supported 0.4, emergency 0.3, tool 0.9) and thresholds are fit on the dev `fit` split and frozen in [`configs/gate_frozen.json`](configs/gate_frozen.json).

## Results

### 1. Synthetic development set (`val` split, n = 288; 24 emergencies, 216 non-emergencies)

| System | Acc. | Missed emerg. | Over-triage | Wrong tool calls | Wrong answers |
|---|---|---|---|---|---|
| B0 always answer | 0.333 | 24/24 | 0/216 | 0/0 | 192 |
| B1 retrieval-score threshold (mE5-large cosine) | 0.573 | 24/24 | 0/216 | 0/0 | 27 |
| B3 d1-3B, single five-way question | 0.733 | 18/24 | 0/216 | 0/14 | 23 |
| B2 Qwen2.5-0.5B, decomposed gate | 0.083 | 0/24 | 216/216 | 0/0 | 0 |
| B2 Qwen2.5-1.5B, decomposed gate | 0.191 | 0/24 | 179/216 | 0/8 | 4 |
| **Ours: d1-3B, decomposed gate** | **0.865** (CI 0.813–0.915) | **0/24** | **2/216** | **0/42** | **5** |

- `supported` score: AUROC 0.986 (cosine 0.944), ECE 0.107 → 0.019 after temperature scaling.
- Qwen scorers say "emergency" for every query (240/240); averaging original and reversed option order does not fix it (0.083 / 0.233).
- Retrieval R@1 on dialect queries that differ from standard (fit, n = 72): multilingual-e5-large 0.931 · bge-m3 0.889 · bangla-e5-small (prefix) 0.778 · multilingual-e5-small 0.736. Standard vs dialect R@1 equal within noise: the synthetic dialect text is too mild to show a dialect effect.

### 2. Native-speaker pilot (frozen configuration, nothing tuned)

49 base queries rendered by native speakers into four dialects (160 instances) plus the 49 standard-Bengali originals as control. Retrieval and gate run end to end.

| Rendering | n | R@1 | Action accuracy (95% CI) | Missed emerg. | Wrong answers |
|---|---|---|---|---|---|
| Standard (control) | 49 | 1.000 | 0.857 (0.755–0.939) | 0/4 | 0 |
| Barishal | 40 | 0.905 | 0.675 (0.525–0.800) | 1/3 | 0 |
| Chittagong | 39 | 0.700 | 0.333 (0.205–0.487) | 1/2 | 0 |
| Rajshahi | 32 | 0.875 | 0.812 (0.688–0.938) | 0/2 | 0 |
| Rangpur | 49 | 0.926 | 0.612 (0.469–0.735) | 1/4 | 0 |
| **Native pooled** | **160** | **0.857** | **0.600 (0.510–0.687)** | **3/11** | **0** |

Main findings:
- **The safety property does not transfer to native dialect text.** The gate mostly over-abstains (36/73 answerable queries refused) and misses 3/11 emergencies.
- All three missed emergencies occur where **retrieval returned the wrong passage**; with the gold passage none is missed (0/11). The emergency question depends on the retrieved passage.
- Rankings survive (emergency AUROC 1.000 → 0.957, answerability AUROC 0.993 → 0.923) but calibrated values drop (median P(emergency) on emergencies 0.964 → 0.325): a **calibration shift** from synthetic to native text.
- **Revision analyses (E7, E8):** temperature scaling fit on synthetic data *worsens* calibration of P(supported) on native dialect text (ECE 0.091 → 0.209). An independent query-only emergency check (fit on dev only) is weaker alone, but OR-ed with the passage-conditioned check it catches all 11 native emergencies, at the cost of over-triage rising from 1 to 29 of 149.

## Caveats

- Dev data (queries, labels, KB passages, dialect text) were written with an LLM assistant; dev dialect text is rule-based/synthetic and not validated by native speakers.
- The emergency question was reworded once after errors on `val` (first wording: 0.83 acc, 2 missed emergencies, 9/216 over-triage), so `val` numbers are optimistic.
- Native pilot is small (49 base queries, 11 emergencies from 4 base queries, 32–49 instances per dialect). Dialects cover different base queries, and the protocol differs: Chittagong was written from scratch, the others were mostly native corrections of LLM drafts. Per-dialect numbers are not a ranking of dialects.
- Ambiguous-query accuracy is weak (0.61 on `val`): the `specific` question is not used in the decision rule.
- Grounding uses a gazetteer and may reject dialectal spellings of place names.
- Compute numbers are Kaggle T4 (fp16, ~365 ms per five questions, ~6.4 GB), **not** edge-device profiling.
- 14 KB passages are flagged `check` (facts not yet verified). Content is for research evaluation, not medical or agricultural advice.

## Repository layout

```
data/            knowledge_base/  queries/ (base queries + native dialect renderings)
                 dev/  gate/ (typed question sets v1, v2)  native/ (native_eval_v1.csv)
src/aisis/       paths.py  data_build/ (reproducible builders)
                 gate/ (grounding, calibration, decision, metrics, selection)
                 retrieval/ (placeholder)
scripts/         analyze_gate.py  analyze_retrieval.py  analyze_baselines.py
                 build_native_set.py  analyze_native.py  git_commit_plan.sh
notebooks/       01 d1 gate · 02 Laya pilot · 03 retrieval baselines · 04 retrieval score (B1)
                 05 Qwen gate · 06 Qwen gate, option-order debiased · 07 native end-to-end   (Kaggle)
results/         gate_pilot/  gate_dev/  retrieval/  baselines/  native/   (raw per-instance outputs)
configs/         gate_frozen.json   (frozen temperatures + thresholds)
docs/            EXPERIMENTS.md  DATA_CARD.md
tests/           pytest unit tests (gate logic, baseline metrics)
```

## Reproduce

```bash
pip install -r requirements.txt

# datasets (deterministic; verified identical to the committed files)
for f in build_queries build_kb build_dev_pilot build_dev_full; do python src/aisis/data_build/$f.py; done
python scripts/build_native_set.py        # -> data/native/native_eval_v1.csv

# analyses (from committed raw outputs)
python scripts/analyze_gate.py            # fits temperatures/thresholds on `fit`, reports `val`
python scripts/analyze_retrieval.py
python scripts/analyze_baselines.py       # B0–B3 and Qwen scorers on `val`
python scripts/analyze_native.py          # native pilot with the frozen config
pytest -q
```

Model inference (d1-3B, Qwen2.5, embedding models) runs on a Kaggle T4 via the notebooks; raw outputs are committed under `results/`.

**Author:** Tariqul Islam