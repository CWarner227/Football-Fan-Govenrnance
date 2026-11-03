"""Potential eligible voting power, independent of ballots actually cast."""

import math
from collections.abc import Sequence

import numpy as np


def concentration_metrics(weights: Sequence[float]) -> dict[str, float | None]:
    values = np.asarray(weights, dtype=float)
    if values.ndim != 1 or not np.isfinite(values).all() or (values < 0).any():
        raise ValueError("Voting weights must be finite, nonnegative, one-dimensional")
    keys = (
        "gini",
        "effective_voters",
        "max_power_share",
        "top_1_share",
        "top_5_share",
        "top_10_share",
    )
    if not values.size or values.max() == 0:
        return dict.fromkeys(keys)
    # Scaling avoids overflow in sums and squared sums for large valid weights.
    shares = np.sort(values / values.max())
    shares /= shares.sum()
    n = shares.size
    result = {
        "gini": float(np.clip(2 * np.dot(np.arange(1, n + 1) / n, shares) - (n + 1) / n, 0, 1)),
        "effective_voters": float(1 / np.dot(shares, shares)),
        "max_power_share": float(shares[-1]),
    }
    for percentage in (1, 5, 10):
        count = max(1, math.ceil(n * percentage / 100))
        result[f"top_{percentage}_share"] = float(shares[-count:].sum())
    return result
