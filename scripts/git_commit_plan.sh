#!/usr/bin/env bash
# Creates a logical commit history for this repo. Run once, in the repo root.
# Uses YOUR git identity (git config user.name / user.email). Does not backdate anything.
# Usage: bash scripts/git_commit_plan.sh [remote_url]
set -euo pipefail
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || git init -b main
git config user.name >/dev/null || { echo "Set git user.name first"; exit 1; }
git config user.email >/dev/null || { echo "Set git user.email first"; exit 1; }

TRAILER=$'\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_01Q4tgq3PHcer1GQVjk5r4rr'
c() { local msg="$1"; shift; git add -- "$@"; git commit -q -m "$msg$TRAILER"; echo "committed: $msg"; }

c "chore: add .gitignore, requirements and package skeleton" .gitignore requirements.txt src/aisis/__init__.py src/aisis/paths.py src/aisis/data_build/__init__.py src/aisis/gate/__init__.py src/aisis/retrieval/__init__.py
c "data: add 200 base queries and builder script" data/queries src/aisis/data_build/build_queries.py
c "data: add 136-passage knowledge base and builder" data/knowledge_base src/aisis/data_build/build_kb.py
c "data: add pilot dev set (60 rows), gate question v1 and builder" data/dev/AISIS_DevSet_Pilot_v1.xlsx data/gate/gate_questions_v1.json src/aisis/data_build/build_dev_pilot.py
c "data: add full dev set (400 rows, fit/val) and builder" data/dev/AISIS_DevSet_v1.xlsx src/aisis/data_build/build_dev_full.py
c "gate: add d1/Laya pilot notebooks and pilot results" notebooks/01_gate_d1_kaggle.ipynb notebooks/02_gate_laya_pilot_kaggle.ipynb results/gate_pilot
c "gate: add d1 dev results with v1 emergency wording" results/gate_dev/results_d1_dev_gate-v1.csv
c "gate: reword emergency question (v2) and add v2 dev results" data/gate/gate_questions_v2.json results/gate_dev/results_d1_dev_gate-v2.csv
c "gate: add grounding, calibration, decision and metrics modules" src/aisis/gate/grounding.py src/aisis/gate/calibration.py src/aisis/gate/decision.py src/aisis/gate/metrics.py
c "gate: add analysis script and freeze selected config" scripts/analyze_gate.py configs
c "test: add unit tests for gate logic" tests
c "retrieval: add baseline notebook, raw results and analysis script" notebooks/03_baseline_retrieval_kaggle.ipynb results/retrieval scripts/analyze_retrieval.py
c "docs: add README, experiment log and data card" README.md docs scripts/git_commit_plan.sh

[ -z "$(git status --porcelain)" ] || { echo "WARNING: uncommitted files remain:"; git status --short; exit 1; }
if [ "${1:-}" != "" ]; then git remote add origin "$1" 2>/dev/null || git remote set-url origin "$1"; git push -u origin main; fi
git log --oneline
