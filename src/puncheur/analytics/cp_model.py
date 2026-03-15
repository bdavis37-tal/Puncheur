"""Critical Power / W' model fitting — the physiological engine.

Fits the 2-parameter CP model (Morton 1996) to a rider's power-duration data:

    P(t) = CP + W' / t

Where:
    CP  = Critical Power — the highest power sustainable indefinitely
          (in practice, ~40-70 min boundary between aerobic and anaerobic)
    W'  = Work capacity above CP — the finite anaerobic energy reservoir (joules)
    t   = Duration in seconds

This replaces generic FTP multipliers with a real physiological model fit
to the rider's own data. Given any target duration, we can predict the
exact power the rider should be able to sustain.

Why this matters for acquisition:
- Strava/Garmin use FTP as a single number. We model the full power-duration
  relationship, which means we can predict performance at ANY duration.
- The model is fit from actual ride data, not estimated from a 20-min test.
- W' from the model is physiologically validated, not a guess from "experience level."
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from puncheur.models.ride import Ride


@dataclass
class CPModel:
    """Fitted Critical Power model.

    Attributes:
        cp: Critical Power in watts (aerobic ceiling).
        w_prime: W' in joules (anaerobic work capacity above CP).
        r_squared: Goodness of fit (1.0 = perfect).
        durations_used: Number of data points used in fitting.
    """

    cp: float
    w_prime: float
    r_squared: float
    durations_used: int

    def predict_power(self, duration_seconds: int) -> float:
        """Predict max sustainable power for a given duration.

        Uses the hyperbolic model: P = CP + W'/t
        For very short durations (<5s), caps at a neuromuscular ceiling.

        Args:
            duration_seconds: Target effort duration.

        Returns:
            Predicted power in watts.
        """
        if duration_seconds <= 0:
            return 0.0

        # Hyperbolic model
        power = self.cp + self.w_prime / duration_seconds

        # Neuromuscular ceiling: ~2.5x CP for sprints
        max_neuromuscular = self.cp * 2.5
        return min(power, max_neuromuscular)

    def predict_duration(self, target_power: float) -> float:
        """Predict how long a given power can be sustained.

        Inverts the model: t = W' / (P - CP)
        If target_power <= CP, returns infinity (sustainable).

        Args:
            target_power: Power to sustain in watts.

        Returns:
            Duration in seconds, or float('inf') if below CP.
        """
        if target_power <= self.cp:
            return float("inf")
        return self.w_prime / (target_power - self.cp)

    def time_to_exhaustion(self, power: float) -> float:
        """Alias for predict_duration — more intuitive name."""
        return self.predict_duration(power)

    def w_cost(self, power: float, duration_seconds: int) -> float:
        """Calculate W' expenditure for a given effort.

        Args:
            power: Average power in watts.
            duration_seconds: Duration of effort.

        Returns:
            W' cost in joules. Zero if power is below CP.
        """
        above_cp = max(0.0, power - self.cp)
        return above_cp * duration_seconds

    def depletion_pct(self, power: float, duration_seconds: int) -> float:
        """Percentage of W' depleted by a given effort.

        Args:
            power: Average power in watts.
            duration_seconds: Duration of effort.

        Returns:
            Percentage of W' used (can exceed 100% = unsustainable).
        """
        if self.w_prime <= 0:
            return 0.0
        return (self.w_cost(power, duration_seconds) / self.w_prime) * 100


def fit_cp_model(
    curve: list[tuple[int, float]],
    min_duration: int = 120,
    max_duration: int = 1200,
) -> CPModel:
    """Fit a CP/W' model from a power-duration curve.

    Uses linear regression on the work-duration relationship:
        Work(t) = W' + CP * t

    Where Work = Power * duration. This linearization allows a simple
    OLS fit that's robust and interpretable.

    Args:
        curve: Power-duration curve as (duration, power) tuples.
        min_duration: Minimum duration to include (default 120s = 2 min).
            Excludes sprint/neuromuscular data that doesn't fit the
            aerobic model.
        max_duration: Maximum duration to include (default 1200s = 20 min).

    Returns:
        Fitted CPModel with CP, W', and R-squared.
    """
    # Filter to the physiologically valid range for the 2-parameter model
    points = [
        (d, p) for d, p in curve if min_duration <= d <= max_duration and p > 0
    ]

    if len(points) < 3:
        # Not enough data — fall back to simple estimation
        return _estimate_from_sparse_data(curve)

    # Linearize: Work = CP * t + W'
    # This is y = m*x + b where y=Work, x=t, m=CP, b=W'
    durations = np.array([d for d, _ in points], dtype=float)
    powers = np.array([p for _, p in points], dtype=float)
    work = powers * durations  # Total work in joules

    # OLS: fit Work = CP * t + W'
    # Design matrix: [t, 1]
    A = np.column_stack([durations, np.ones(len(durations))])
    result, residuals, _, _ = np.linalg.lstsq(A, work, rcond=None)

    cp = float(result[0])
    w_prime = float(result[1])

    # Sanity bounds
    cp = max(50, min(cp, 500))  # CP between 50-500W
    w_prime = max(5000, min(w_prime, 40000))  # W' between 5-40kJ

    # R-squared
    ss_res = float(np.sum((work - A @ result) ** 2))
    ss_tot = float(np.sum((work - np.mean(work)) ** 2))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    return CPModel(
        cp=round(cp, 1),
        w_prime=round(w_prime),
        r_squared=round(r_squared, 4),
        durations_used=len(points),
    )


def _estimate_from_sparse_data(curve: list[tuple[int, float]]) -> CPModel:
    """Fallback estimation when there's not enough data for a proper fit.

    Uses the 20-min power (if available) as an FTP proxy and estimates
    W' from the difference between short and long efforts.
    """
    powers_by_dur = dict(curve)

    # Best estimates from available data
    p20 = powers_by_dur.get(1200, 0)
    p5 = powers_by_dur.get(300, 0)
    p1 = powers_by_dur.get(60, 0)

    if p20 > 0:
        cp = p20 * 0.95  # Standard FTP estimation
    elif p5 > 0:
        cp = p5 * 0.85
    elif p1 > 0:
        cp = p1 * 0.70
    else:
        cp = 200  # Default

    # Estimate W' from the gap between short and long power
    if p1 > 0 and cp > 0:
        w_prime = (p1 - cp) * 60  # W' ≈ (1-min power - CP) * 60
    elif p5 > 0 and cp > 0:
        w_prime = (p5 - cp) * 300
    else:
        w_prime = 20000  # Default

    w_prime = max(5000, min(w_prime, 40000))

    return CPModel(
        cp=round(cp, 1),
        w_prime=round(w_prime),
        r_squared=0.0,
        durations_used=0,
    )


def fit_cp_from_ride(ride: Ride) -> CPModel:
    """Convenience: fit a CP model directly from a single ride."""
    from puncheur.analytics.power_curve import power_duration_curve

    curve = power_duration_curve(ride)
    return fit_cp_model(curve)


def fit_cp_from_rides(rides: list[Ride]) -> CPModel:
    """Fit a CP model from multiple rides (composite best efforts)."""
    from puncheur.analytics.power_curve import composite_power_curve

    curve = composite_power_curve(rides)
    return fit_cp_model(curve)
