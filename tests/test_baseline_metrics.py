import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import numpy as np
from aisis.gate.metrics import auroc, aurc, best_thr


def test_auroc_perfect_and_reversed_and_tie():
    assert auroc([.9, .8, .2, .1], [1, 1, 0, 0]) == 1.0
    assert auroc([.1, .2, .8, .9], [1, 1, 0, 0]) == 0.0
    assert auroc([.5, .5, .5, .5], [1, 1, 0, 0]) == 0.5


def test_aurc_ordering():
    good = aurc([.9, .8, .2, .1], [1, 1, 0, 0])
    bad = aurc([.1, .2, .8, .9], [1, 1, 0, 0])
    assert abs(good - (0 + 0 + 1/3 + 2/4) / 4) < 1e-9   # risk at 1,2,3,4 accepted items
    assert bad > good


def test_best_thr_separates():
    t = best_thr([.9, .8, .3, .2], [1, 1, 0, 0])
    assert .3 < t <= .8
