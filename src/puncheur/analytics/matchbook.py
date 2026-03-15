"""W'bal (W-prime balance) tracking — the match burning model.

Implements the Skiba (2012) differential W'bal model to track anaerobic
capacity depletion and recovery throughout a ride. W' represents the finite
work capacity above FTP. When you "burn a match" (surge above FTP), W'
depletes. When you ride below FTP, it recovers exponentially.

This is the analytical heart of Puncheur — it answers "how many matches
did I have left going into that final climb?"
"""

from __future__ import annotations

import numpy as np


def compute_wbal(
    power: np.ndarray,
    ftp: float,
    w_prime: float,
) -> np.ndarray:
    """Compute W'bal (W-prime balance) over a power stream.

    Uses the differential method (Skiba 2012):
    - When power > FTP: W'bal decreases by (power - FTP) per second
    - When power <= FTP: W'bal recovers toward W' with exponential time constant
      tau = 546 * e^(-0.01 * (FTP - power)) + 316

    Args:
        power: Array of power values in watts (1Hz, one per second).
        ftp: Functional Threshold Power in watts.
        w_prime: W' (W-prime) capacity in joules.

    Returns:
        Array of W'bal values in joules, same length as power.
    """
    n = len(power)
    if n == 0:
        return np.array([])

    wbal = np.zeros(n, dtype=float)
    wbal[0] = w_prime

    for i in range(1, n):
        p = power[i]
        if p > ftp:
            # Depleting: W'bal decreases by (power - FTP) joules this second
            wbal[i] = wbal[i - 1] - (p - ftp)
        else:
            # Recovering: exponential recovery toward W'
            tau = 546.0 * np.exp(-0.01 * (ftp - p)) + 316.0
            wbal[i] = w_prime - (w_prime - wbal[i - 1]) * np.exp(-1.0 / tau)

        # W'bal can't exceed W' or go below 0
        wbal[i] = np.clip(wbal[i], 0.0, w_prime)

    return wbal


def count_matches_burned(
    power: np.ndarray,
    ftp: float,
    threshold_pct: float = 1.20,
    min_duration_s: int = 30,
) -> int:
    """Count distinct "matches burned" — hard efforts above threshold.

    A match is a continuous effort above threshold_pct * FTP lasting
    at least min_duration_s seconds.

    Args:
        power: Array of power values in watts.
        ftp: Functional Threshold Power in watts.
        threshold_pct: Power threshold as fraction of FTP (default 120%).
        min_duration_s: Minimum duration in seconds for a match.

    Returns:
        Number of matches burned.
    """
    threshold = ftp * threshold_pct
    above = power > threshold

    matches = 0
    current_duration = 0

    for is_above in above:
        if is_above:
            current_duration += 1
        else:
            if current_duration >= min_duration_s:
                matches += 1
            current_duration = 0

    # Check final effort
    if current_duration >= min_duration_s:
        matches += 1

    return matches


def wbal_at_timestamp(
    wbal: np.ndarray,
    timestamp_index: int,
) -> float:
    """Get W'bal value at a specific timestamp index.

    Args:
        wbal: W'bal array from compute_wbal.
        timestamp_index: Index into the array.

    Returns:
        W'bal value in joules, or 0.0 if index out of range.
    """
    if 0 <= timestamp_index < len(wbal):
        return float(wbal[timestamp_index])
    return 0.0


def matches_remaining(
    current_wbal: float,
    segment_demands: list[float],
) -> int:
    """Estimate how many segments can be covered with remaining W'bal.

    Args:
        current_wbal: Current W'bal in joules.
        segment_demands: List of estimated W' cost for each upcoming segment.

    Returns:
        Number of segments that can be covered before W'bal depletion.
    """
    remaining = current_wbal
    count = 0
    for demand in segment_demands:
        if remaining >= demand:
            remaining -= demand
            count += 1
        else:
            break
    return count
