"""Wealth ranks of the full eligible electorate, with potential and cast power."""

import math
from collections.abc import Sequence

import numpy as np


def representation_metrics(
    identities: Sequence[str],
    wealth: Sequence[float],
    contributions: Sequence[float],
    eligible_weights: Sequence[float],
    cast_identities: Sequence[str],
    cast_weights: Sequence[float],
) -> dict:
    n = len(identities)
    if not (len(wealth) == len(contributions) == len(eligible_weights) == n):
        raise ValueError("Representation inputs must have matching lengths")
    if len(set(identities)) != n or len(cast_identities) != len(cast_weights):
        raise ValueError("Representation requires unique identities and aligned ballots")
    money = np.asarray(contributions, dtype=float)
    power = np.asarray(eligible_weights, dtype=float)
    assets = np.asarray(wealth, dtype=float)
    cast_power = np.zeros(n)
    positions = {identity: i for i, identity in enumerate(identities)}
    cast_mask = np.zeros(n, dtype=bool)
    for identity, weight in zip(cast_identities, cast_weights, strict=True):
        if identity not in positions or cast_mask[positions[identity]]:
            raise ValueError("Invalid or duplicate cast identity")
        position = positions[identity]
        cast_power[position] = weight
        cast_mask[position] = True
    if any(not np.isfinite(v).all() or (v < 0).any() for v in (money, power, assets, cast_power)):
        raise ValueError("Representation values must be finite and nonnegative")
    order = np.lexsort((np.asarray(identities, dtype=str), assets))
    masks = {}
    bottom = np.zeros(n, dtype=bool)
    bottom[order[: n // 2]] = True
    masks["bottom_50"] = bottom
    for percentage in (10, 1):
        mask = np.zeros(n, dtype=bool)
        if n:
            mask[order[-math.ceil(n * percentage / 100) :]] = True
        masks[f"top_{percentage}"] = mask

    def shares(values):
        if not n or values.max(initial=0) == 0:
            return None
        scaled = values / values.max()
        return scaled / scaled.sum()

    output = {}
    for name, weights, funding in [
        ("potential", power, money),
        ("realized", cast_power, money * cast_mask),
    ]:
        weight_shares, funding_shares = shares(weights), shares(funding)
        result = {}
        for label, mask in masks.items():
            w = float(weight_shares[mask].sum()) if weight_shares is not None else None
            c = float(funding_shares[mask].sum()) if funding_shares is not None else None
            result[f"{label}_wealth_power_share"] = w
            result[f"{label}_contribution_share"] = c
            result[f"{label}_contribution_to_power_ratio"] = c / w if c is not None and w else None
        deciles = {}
        for decile in range(10):
            group = order[np.arange(n) * 10 // max(n, 1) == decile]
            deciles[str((decile + 1) * 10)] = (
                float(weight_shares[group].sum()) if weight_shares is not None else None
            )
        result["wealth_decile_power_shares"] = deciles
        output[name] = result
    return output
