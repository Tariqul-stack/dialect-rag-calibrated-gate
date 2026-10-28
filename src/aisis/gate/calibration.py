"""Temperature scaling on d1's typed-choice probabilities + ECE."""
import numpy as np


def temp(p, T):
    v = np.array(list(p.values()), float).clip(1e-9)
    v = v ** (1 / T)
    v /= v.sum()
    return dict(zip(p.keys(), v))


def nll(probs, golds, T):
    return float(np.mean([-np.log(max(temp(p, T)[g], 1e-9)) for p, g in zip(probs, golds)]))


def fit_temperature(probs, golds, grid=None):
    grid = np.round(np.arange(0.3, 4.01, 0.1), 2) if grid is None else grid
    return float(min(grid, key=lambda T: nll(probs, golds, T)))


def ece(conf, ok, bins=10):
    conf, ok = np.array(conf), np.array(ok)
    e = 0.0
    edges = np.linspace(0.5, 1.0, bins // 2 + 1)
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf >= lo) & ((conf < hi) | (hi == 1.0))
        if m.sum():
            e += m.sum() / len(conf) * abs(conf[m].mean() - ok[m].mean())
    return float(e)
