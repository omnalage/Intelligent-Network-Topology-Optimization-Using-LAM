"""
Step 2: Baseline policy (no learning).

Implements:
    select_best_router_by_score(state)

Policy:
1) Parse flattened environment state into per-router metrics:
       [occupancy, chr, latency, cmba]
2) Normalize each metric across routers.
3) Compute:
       score = CMBA + CHR - latency - occupancy
4) Return router index with maximum score.
"""

from __future__ import annotations

from typing import Dict, Tuple

import numpy as np


def _minmax_normalize(x: np.ndarray) -> np.ndarray:
    """Min-max normalize to [0, 1], safe for constant vectors."""
    x = np.asarray(x, dtype=np.float32)
    mn = float(np.min(x))
    mx = float(np.max(x))
    if abs(mx - mn) < 1e-12:
        return np.ones_like(x, dtype=np.float32)
    return (x - mn) / (mx - mn)


def select_best_router_by_score(state: np.ndarray) -> int:
    """
    Baseline router selection policy (no RL learning).

    Args:
        state: flattened vector from CacheEnvironment:
               [occ, chr, lat, cmba, occ, chr, lat, cmba, ...]

    Returns:
        int: router index with maximum baseline score.
    """
    s = np.asarray(state, dtype=np.float32).reshape(-1)
    if s.size == 0 or s.size % 4 != 0:
        raise ValueError("state must be a non-empty flattened vector with length multiple of 4")

    # Reshape to N x 4 in fixed order: [occupancy, chr, latency, cmba]
    metrics = s.reshape(-1, 4)
    occupancy = metrics[:, 0]
    chr_val = metrics[:, 1]
    latency = metrics[:, 2]
    cmba = metrics[:, 3]

    # Normalize all metrics per current state
    n_occ = _minmax_normalize(occupancy)
    n_chr = _minmax_normalize(chr_val)
    n_lat = _minmax_normalize(latency)
    n_cmba = _minmax_normalize(cmba)

    # Baseline score (as requested)
    scores = n_cmba + n_chr - n_lat - n_occ
    best_idx = int(np.argmax(scores))
    return best_idx


def select_best_router_with_debug(state: np.ndarray) -> Tuple[int, Dict[str, np.ndarray]]:
    """
    Optional helper for explainability in reports/debugging.
    Returns selected index plus intermediate vectors.
    """
    s = np.asarray(state, dtype=np.float32).reshape(-1)
    if s.size == 0 or s.size % 4 != 0:
        raise ValueError("state must be a non-empty flattened vector with length multiple of 4")

    metrics = s.reshape(-1, 4)
    occupancy = metrics[:, 0]
    chr_val = metrics[:, 1]
    latency = metrics[:, 2]
    cmba = metrics[:, 3]

    n_occ = _minmax_normalize(occupancy)
    n_chr = _minmax_normalize(chr_val)
    n_lat = _minmax_normalize(latency)
    n_cmba = _minmax_normalize(cmba)
    scores = n_cmba + n_chr - n_lat - n_occ
    best_idx = int(np.argmax(scores))

    debug = {
        "occupancy": occupancy,
        "chr": chr_val,
        "latency": latency,
        "cmba": cmba,
        "n_occupancy": n_occ,
        "n_chr": n_chr,
        "n_latency": n_lat,
        "n_cmba": n_cmba,
        "scores": scores,
    }
    return best_idx, debug


if __name__ == "__main__":
    # Tiny sanity check
    # 2 routers -> [occ, chr, lat, cmba] * 2
    dummy_state = np.array([5, 0.6, 40, 0.5, 2, 0.5, 20, 0.4], dtype=np.float32)
    idx, dbg = select_best_router_with_debug(dummy_state)
    print("Selected router index:", idx)
    print("Scores:", dbg["scores"])
