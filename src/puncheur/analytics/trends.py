"""Ride-over-ride trend analysis.

Tracks segment power, duration, and W'bal trends over weeks for rides
on the same tagged route. Shows improvement or regression on each segment
with simple moving averages and percentage changes.
"""

from __future__ import annotations

import json
from pathlib import Path

from puncheur.config import get_rides_dir


def save_ride_result(
    route_name: str,
    ride_date: str,
    avg_power: float,
    normalized_power: float,
    tss: float,
    segment_results: list[dict] | None = None,
) -> None:
    """Save a ride result to the history file for a route.

    Args:
        route_name: Name of the route.
        ride_date: Date string (ISO format).
        avg_power: Average power in watts.
        normalized_power: Normalized power in watts.
        tss: Training Stress Score.
        segment_results: Optional list of per-segment results.
    """
    rides_dir = get_rides_dir()
    slug = route_name.lower().replace(" ", "_")
    history_file = rides_dir / f"{slug}_history.json"

    history: list[dict] = []
    if history_file.exists():
        history = json.loads(history_file.read_text(encoding="utf-8"))

    entry = {
        "date": ride_date,
        "avg_power": avg_power,
        "np": normalized_power,
        "tss": tss,
        "segments": segment_results or [],
    }
    history.append(entry)

    history_file.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")


def load_route_history(route_name: str) -> list[dict]:
    """Load ride history for a route.

    Args:
        route_name: Name of the route.

    Returns:
        List of ride result dicts, sorted by date.
    """
    rides_dir = get_rides_dir()
    slug = route_name.lower().replace(" ", "_")
    history_file = rides_dir / f"{slug}_history.json"

    if not history_file.exists():
        return []

    history = json.loads(history_file.read_text(encoding="utf-8"))
    return sorted(history, key=lambda x: x.get("date", ""))


def compute_trends(history: list[dict]) -> dict:
    """Compute trend metrics from ride history.

    Args:
        history: List of ride result dicts.

    Returns:
        Dict with trend analysis including moving averages and percentage changes.
    """
    if len(history) < 2:
        return {"trend": "insufficient_data", "rides": len(history)}

    recent = history[-3:]  # Last 3 rides
    older = history[:-3] if len(history) > 3 else history[:1]

    recent_avg_power = sum(r.get("avg_power", 0) for r in recent) / len(recent)
    older_avg_power = sum(r.get("avg_power", 0) for r in older) / len(older)

    power_change_pct = 0.0
    if older_avg_power > 0:
        power_change_pct = ((recent_avg_power - older_avg_power) / older_avg_power) * 100

    recent_tss = sum(r.get("tss", 0) for r in recent) / len(recent)
    older_tss = sum(r.get("tss", 0) for r in older) / len(older)

    if power_change_pct > 3:
        trend = "improving"
    elif power_change_pct < -3:
        trend = "declining"
    else:
        trend = "stable"

    return {
        "trend": trend,
        "rides": len(history),
        "recent_avg_power": recent_avg_power,
        "older_avg_power": older_avg_power,
        "power_change_pct": power_change_pct,
        "recent_avg_tss": recent_tss,
        "older_avg_tss": older_tss,
    }
