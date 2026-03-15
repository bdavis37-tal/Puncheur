"""Mean Maximal Power (MMP) curve calculation.

Computes the power duration curve from ride data — the maximum average power
achievable for every duration from 1 second to 60 minutes. This is the
foundation for all performance analysis in Puncheur.
"""

from __future__ import annotations

import numpy as np

from puncheur.models.ride import Ride


def power_duration_curve(
    ride: Ride,
    max_duration: int = 3600,
) -> list[tuple[int, float]]:
    """Calculate the mean maximal power curve from a single ride.

    For each duration from 1 second to max_duration, finds the highest
    average power sustained over any window of that length.

    Args:
        ride: A Ride object containing power data.
        max_duration: Maximum duration to calculate in seconds (default 3600 = 60 min).

    Returns:
        List of (duration_seconds, max_avg_power) tuples, sorted by duration.
    """
    power = ride.power_stream
    n = len(power)
    if n == 0:
        return []

    # Limit max_duration to available data
    max_duration = min(max_duration, n)

    # Use cumulative sum for efficient rolling averages
    cumsum = np.concatenate(([0], np.cumsum(power)))
    curve: list[tuple[int, float]] = []

    for duration in range(1, max_duration + 1):
        if duration > n:
            break
        # All possible windows of this duration
        window_sums = cumsum[duration:] - cumsum[:-duration]
        max_avg = float(np.max(window_sums)) / duration
        curve.append((duration, max_avg))

    return curve


def composite_power_curve(
    rides: list[Ride],
    max_duration: int = 3600,
) -> list[tuple[int, float]]:
    """Build a composite "best efforts" power curve from multiple rides.

    For each duration, takes the best (highest) average power across
    all provided rides.

    Args:
        rides: List of Ride objects.
        max_duration: Maximum duration to calculate in seconds.

    Returns:
        List of (duration_seconds, max_avg_power) tuples.
    """
    if not rides:
        return []

    # Calculate individual curves
    all_curves: dict[int, float] = {}
    for ride in rides:
        curve = power_duration_curve(ride, max_duration)
        for duration, power in curve:
            if duration not in all_curves or power > all_curves[duration]:
                all_curves[duration] = power

    return sorted(all_curves.items())


def power_at_duration(curve: list[tuple[int, float]], duration: int) -> float:
    """Look up power for a specific duration from a power curve.

    Args:
        curve: A power duration curve.
        duration: Duration in seconds.

    Returns:
        The max average power for that duration, or 0.0 if not available.
    """
    for d, p in curve:
        if d == duration:
            return p
    return 0.0


def duration_buckets(curve: list[tuple[int, float]]) -> dict[str, float]:
    """Extract key duration benchmarks from a power curve.

    Returns power values for standard duration buckets used in
    cycling analysis.
    """
    targets = {
        "5s": 5,
        "10s": 10,
        "30s": 30,
        "1min": 60,
        "2min": 120,
        "5min": 300,
        "10min": 600,
        "20min": 1200,
        "30min": 1800,
        "60min": 3600,
    }
    return {label: power_at_duration(curve, dur) for label, dur in targets.items()}
