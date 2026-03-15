"""Fitness model — CTL/ATL/TSB (Performance Management Chart).

Implements the standard PMC model used in cycling training:
- CTL (Chronic Training Load): 42-day EWMA of daily TSS = "fitness"
- ATL (Acute Training Load): 7-day EWMA of daily TSS = "fatigue"
- TSB (Training Stress Balance): CTL - ATL = "form"

Positive TSB = fresh and ready to perform.
Negative TSB = fatigued and building fitness.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from puncheur.config import get_data_dir
from puncheur.models.rider import Rider

FITNESS_FILE = "fitness_log.json"

# EWMA time constants
CTL_DAYS = 42
ATL_DAYS = 7


def _ewma(values: list[float], time_constant: int) -> list[float]:
    """Compute exponentially weighted moving average.

    Args:
        values: Daily values to smooth.
        time_constant: Time constant in days.

    Returns:
        EWMA values, same length as input.
    """
    if not values:
        return []

    alpha = 2.0 / (time_constant + 1)
    result = [values[0]]
    for v in values[1:]:
        result.append(result[-1] * (1 - alpha) + v * alpha)
    return result


def log_daily_tss(ride_date: str, tss: float) -> None:
    """Log a daily TSS value to the fitness file.

    If multiple rides occur on the same day, TSS values are summed.

    Args:
        ride_date: Date string in ISO format (YYYY-MM-DD).
        tss: Training Stress Score for the ride.
    """
    fitness_path = get_data_dir() / FITNESS_FILE

    log: dict[str, float] = {}
    if fitness_path.exists():
        log = json.loads(fitness_path.read_text(encoding="utf-8"))

    log[ride_date] = log.get(ride_date, 0.0) + tss

    fitness_path.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")


def compute_fitness(days_back: int = 90) -> dict:
    """Compute current CTL, ATL, and TSB from the fitness log.

    Fills in zero-TSS days for accurate EWMA calculation.

    Args:
        days_back: Number of days of history to consider.

    Returns:
        Dict with ctl, atl, tsb, and daily history arrays.
    """
    fitness_path = get_data_dir() / FITNESS_FILE

    log: dict[str, float] = {}
    if fitness_path.exists():
        log = json.loads(fitness_path.read_text(encoding="utf-8"))

    if not log:
        return {"ctl": 0.0, "atl": 0.0, "tsb": 0.0, "history": []}

    # Build daily TSS array
    today = date.today()
    start_date = today - timedelta(days=days_back)

    daily_tss: list[float] = []
    dates: list[str] = []
    current = start_date
    while current <= today:
        date_str = current.isoformat()
        daily_tss.append(log.get(date_str, 0.0))
        dates.append(date_str)
        current += timedelta(days=1)

    # Compute EWMA
    ctl_values = _ewma(daily_tss, CTL_DAYS)
    atl_values = _ewma(daily_tss, ATL_DAYS)
    tsb_values = [c - a for c, a in zip(ctl_values, atl_values)]

    # Build history
    history = [
        {"date": d, "tss": t, "ctl": c, "atl": a, "tsb": s}
        for d, t, c, a, s in zip(dates, daily_tss, ctl_values, atl_values, tsb_values)
    ]

    return {
        "ctl": ctl_values[-1] if ctl_values else 0.0,
        "atl": atl_values[-1] if atl_values else 0.0,
        "tsb": tsb_values[-1] if tsb_values else 0.0,
        "history": history,
    }


def load_fitness_data(rider: Rider) -> dict:
    """Load fitness data for display.

    Args:
        rider: Rider profile (for context).

    Returns:
        Dict with current fitness metrics.
    """
    return compute_fitness()
