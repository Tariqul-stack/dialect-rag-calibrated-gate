"""Repo-relative paths. Set AISIS_ROOT to redirect all I/O (used to verify reproducibility)."""
import os
from pathlib import Path

ROOT = Path(os.environ.get("AISIS_ROOT", Path(__file__).resolve().parents[2]))
DATA = ROOT / "data"
KB_XLSX = DATA / "knowledge_base" / "AISIS_KnowledgeBase_v1.xlsx"
QUERIES_XLSX = DATA / "queries" / "AISIS_Base_Queries_v1.xlsx"
PILOT_XLSX = DATA / "dev" / "AISIS_DevSet_Pilot_v1.xlsx"
DEV_XLSX = DATA / "dev" / "AISIS_DevSet_v1.xlsx"
GATE_Q_V1 = DATA / "gate" / "gate_questions_v1.json"
GATE_Q_V2 = DATA / "gate" / "gate_questions_v2.json"
RESULTS = ROOT / "results"
