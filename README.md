# Knowing When Not to Act: Calibrated Decision Gating for Dialect-Aware Bengali Retrieval Assistants



> **Status: work in progress, dev-stage results only.** Everything reported here comes from a *synthetic dev set* used for design and tuning. No native-speaker test results exist yet. See [`docs/EXPERIMENTS.md`](docs/EXPERIMENTS.md) for the experiment log and [`docs/DATA_CARD.md`](docs/DATA_CARD.md) for data provenance.

## Idea

Assistants for rural Bangladeshi users must (1) understand dialectal Bengali queries, (2) retrieve the right information, and (3) **avoid wrong decisions and wrong tool actions**, on low-compute hardware. The main contribution is a **calibrated decision gate** that decides whether the system should answer, call a tool, ask for clarification, refer to a clinic, or abstain. Evaluation is text-first; voice (ASR/TTS) is a possible extension, not part of the contribution.

```
dialect query -> embedding -> retrieval over 136-passage KB -> generator proposes answer / tool call
              -> CALIBRATED GATE (Liquid AI d1-3B typed questions + rule-based argument grounding)
              -> answer_from_passage | call_tool | ask_clarification | refer_to_clinic | cannot_answer
```

Gate order: (1) emergency check, recall-first → `refer_to_clinic`; (2) tool check plus rule-based argument grounding (place / crop / date / id must be present) → `call_tool` or `ask_clarification`; (3) calibrated `supported` probability → `answer_from_passage` or `cannot_answer`.

## Current results (dev set, `val` split, n = 288 instances; synthetic, see caveats)

n = 120 dev rows × standard/dialect + 48 wrong-passage instances.

| Metric                                  | Decomposed gate (ours)              | d1 5-way `action` (baseline) |
| --------------------------------------- | ----------------------------------- | ------------------------------ |
| Action accuracy                         | **0.865** (95% CI 0.81–0.92) | 0.733                          |
| Missed emergencies                      | 0 / 24                              | –                             |
| Over-triage (false `refer_to_clinic`) | 2 / 216                             | –                             |
| Wrongly executed tool calls             | 0 / 42                              | –                             |
| Wrong-passage → abstain                | 0.92                                | –                             |
| `supported` ECE (raw → temp-scaled)  | 0.107 → 0.019                      | –                             |

Retrieval baselines (R@1, fit split, dialect queries whose text differs from standard, n = 72): multilingual-e5-large 0.931 · bge-m3 0.889 · bangla-e5-small (prefix) 0.778 · multilingual-e5-small 0.736. **The author's own Mamba-based embedding model has not been evaluated in this pipeline yet.**

## Caveats

- Dev data (queries, labels, KB, dialect text) were written by an LLM; dialect text is rule-based/synthetic and unverified by native speakers. A dialect effect is *not* demonstrated on dev (dev is saturated and the dialect text is mild).
- Gate thresholds and temperatures were fit on `fit` and reported on `val`. The emergency question wording was revised after seeing a `val` error (one instance), so `val` is slightly optimistic. The native test set must never be used for tuning.
- Ambiguous-query accuracy is weak (~0.61); reported as a limitation.
- Compute numbers are Kaggle T4 batch numbers, **not** edge-device profiling.
- 14 KB passages are flagged `check` (medical/agricultural facts not yet verified). Content is for research evaluation, not advice.

## Repository layout

```
data/            knowledge_base/ queries/ dev/ gate/       (generated, versioned)
src/aisis/       paths.py  data_build/ (reproducible builders)
                 gate/ (grounding, calibration, decision, metrics)
                 retrieval/ (placeholder for the own-model adapter)
scripts/         analyze_gate.py  analyze_retrieval.py  git_commit_plan.sh
notebooks/       01 d1 gate, 02 Laya baseline, 03 retrieval baselines   (Kaggle; 01-02 reconstructed from cell code)
results/         gate_pilot/ gate_dev/ retrieval/          (raw per-instance outputs)
configs/         gate_frozen.json                          (frozen temperatures + thresholds)
docs/            EXPERIMENTS.md  DATA_CARD.md
tests/           pytest unit tests for the gate logic
```

## Reproduce

```bash
pip install -r requirements.txt
# rebuild datasets (deterministic; verified identical to the committed files)
for f in build_queries build_kb build_dev_pilot build_dev_full; do python src/aisis/data_build/$f.py; done
python scripts/analyze_gate.py        # re-fits temperatures/thresholds on `fit`, reports `val`
python scripts/analyze_retrieval.py
pytest -q
```

Model inference (d1-3B, embedding baselines) runs on a Kaggle T4 via the notebooks; raw outputs are committed under `results/`.

## Not in this repository

Model weights (`*.pt` etc. are git-ignored) and the author's own unpublished embedding model, which belongs to a separate journal paper.

**Author:** Tariqul Islam
